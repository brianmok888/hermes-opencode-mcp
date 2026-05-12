from __future__ import annotations

import asyncio
import re
from dataclasses import replace

from .config import AppConfig
from .models import TaskRecord, utc_now
from .opencode_adapter import OpenCodeAdapter
from .sanitizer import sanitize_text
from .store import InMemoryStore


class TaskExecutor:
    def __init__(self, store: InMemoryStore, config: AppConfig) -> None:
        self._store = store
        self._config = config
        self._adapter = OpenCodeAdapter(config.opencode_bin) if config.executor_mode == 'opencode' else None
        if self._adapter is not None:
            self._adapter.validate()

    async def execute(self, task: TaskRecord) -> None:
        lane = self._store.get_lane(task.lane_id)
        if lane is None:
            task = replace(task, status='failed', completed_at=utc_now(), error='unknown lane')
            self._store.save_task(task)
            return

        self._store.set_lane_state(task.lane_id, 'busy')
        running = replace(
            task,
            status='running',
            started_at=utc_now(),
            metadata=self._merge_metadata(
                task.metadata,
                {
                    'worker_prefix': lane.worker_prefix,
                    'executor_mode': self._config.executor_mode,
                    'dispatch_status': 'running',
                    'dispatch_started_at': utc_now(),
                },
            ),
        )
        self._store.save_task(running)

        try:
            await asyncio.sleep(0.05)
            latest = self._store.get_task(running.task_id) or running
            if latest.cancel_requested:
                cancelled = replace(
                    latest,
                    status='cancelled',
                    completed_at=utc_now(),
                    summary=self._prefix_summary(lane.worker_prefix, 'Task cancelled before execution adapter dispatch.'),
                    metadata=self._merge_metadata(
                        latest.metadata,
                        {
                            'dispatch_status': 'cancelled_before_dispatch',
                            'execution_handle': f'cancelled:{latest.task_id}',
                        },
                    ),
                )
                self._store.save_task(cancelled)
                self._store.set_lane_state(task.lane_id, 'idle')
                return

            if self._config.executor_mode == 'mock':
                summary = sanitize_text(
                    f'Accepted task for lane={task.lane_id} directory={task.directory}. '
                    f'Execution adapter not wired yet; this is the phase-1 skeleton.'
                )
                done = replace(
                    latest,
                    status='succeeded',
                    completed_at=utc_now(),
                    summary=self._prefix_summary(lane.worker_prefix, summary),
                    metadata=self._merge_metadata(
                        latest.metadata,
                        {
                            'dispatch_status': 'completed',
                            'execution_handle': f'mock:{latest.task_id}',
                        },
                    ),
                )
            else:
                result = await self._adapter.run(
                    text=latest.text,
                    directory=latest.directory,
                    agent=latest.metadata.get('agent'),
                    session_id=latest.metadata.get('session_id'),
                    timeout_ms=int(latest.metadata.get('timeout_ms', 300000)),
                    cancel_check=lambda: bool((self._store.get_task(latest.task_id) or latest).cancel_requested),
                )
                if result.cancelled:
                    done = replace(
                        latest,
                        status='cancelled',
                        completed_at=utc_now(),
                        summary=self._prefix_summary(lane.worker_prefix, 'Task cancelled during execution.'),
                        error=self._prefix_summary(lane.worker_prefix, sanitize_text(result.error or 'opencode execution cancelled during execution')),
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {'dispatch_status': 'cancelled_during_execution'},
                            result.metadata or {},
                        ),
                    )
                elif result.error:
                    done = replace(
                        latest,
                        status='failed',
                        completed_at=utc_now(),
                        error=self._prefix_summary(lane.worker_prefix, sanitize_text(result.error)),
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {'dispatch_status': 'failed'},
                            result.metadata or {},
                        ),
                    )
                else:
                    validated_summary = self._normalize_worker_identity(lane.worker_prefix, result.summary)
                    done = replace(
                        latest,
                        status='succeeded',
                        completed_at=utc_now(),
                        summary=validated_summary,
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {'dispatch_status': 'completed'},
                            result.metadata or {},
                        ),
                    )
            self._store.save_task(done)
            self._store.set_lane_state(task.lane_id, 'idle')
        except Exception as exc:  # pragma: no cover
            failed = replace(
                running,
                status='failed',
                completed_at=utc_now(),
                error=self._prefix_summary(lane.worker_prefix, sanitize_text(str(exc))),
                metadata=self._merge_metadata(
                    running.metadata,
                    {'dispatch_status': 'failed_before_completion'},
                ),
            )
            self._store.save_task(failed)
            self._store.set_lane_state(task.lane_id, 'degraded', error=failed.error)

    @staticmethod
    def _prefix_summary(prefix: str, text: str) -> str:
        stripped = (text or '').strip()
        if not stripped:
            return prefix
        if stripped.startswith(prefix):
            return stripped
        return f'{prefix} {stripped}'

    @staticmethod
    def _normalize_worker_identity(expected_prefix: str, text: str) -> str:
        stripped = sanitize_text((text or '').strip())
        if not stripped:
            return expected_prefix
        lines = stripped.splitlines()
        first_line = lines[0].strip()
        if re.match(r'^oc@[^\s:]+@[^\s:]+:\s*', first_line) and not first_line.startswith(expected_prefix):
            first_line = re.sub(r'^oc@[^\s:]+@[^\s:]+:\s*', '', first_line, count=1).strip()
            lines[0] = first_line
            stripped = '\n'.join(lines).strip()
        return TaskExecutor._prefix_summary(expected_prefix, stripped)

    @staticmethod
    def _merge_metadata(*parts: dict) -> dict:
        merged: dict = {}
        for part in parts:
            if part:
                merged.update(part)
        return merged
