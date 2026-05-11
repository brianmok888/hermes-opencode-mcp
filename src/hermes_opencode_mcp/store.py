from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from threading import RLock
from typing import Any

from .logging_utils import get_logger
from .models import ExecutionTarget, TaskRecord, utc_now


logger = get_logger(__name__)


class PersistentStore:
    def __init__(self, execution_targets: dict[str, ExecutionTarget], state_dir: Path) -> None:
        self._lock = RLock()
        self._state_dir = state_dir
        self._targets_path = state_dir / "targets_state.json"
        self._tasks_path = state_dir / "tasks_state.json"
        self._targets = dict(execution_targets)
        self._tasks: dict[str, TaskRecord] = {}
        self._load_state()
        self._merge_targets(execution_targets)
        self._persist_targets()
        self._persist_tasks()

    def targets(self) -> list[ExecutionTarget]:
        with self._lock:
            return list(self._targets.values())

    def get_target(self, target_id: str) -> ExecutionTarget | None:
        with self._lock:
            return self._targets.get(target_id)

    def set_target_state(self, target_id: str, state: str, error: str | None = None) -> ExecutionTarget:
        with self._lock:
            target = self._targets[target_id]
            updated = replace(target, state=state, last_error=error, updated_at=utc_now())
            self._targets[target_id] = updated
            self._persist_targets()
            return updated

    def add_task(self, task: TaskRecord) -> None:
        with self._lock:
            self._tasks[task.task_id] = task
            self._persist_tasks()

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def save_task(self, task: TaskRecord) -> None:
        with self._lock:
            self._tasks[task.task_id] = task
            self._persist_tasks()

    def request_cancel(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if task.status in {"succeeded", "failed", "cancelled"}:
                return task
            updated = replace(task, cancel_requested=True)
            self._tasks[task_id] = updated
            self._persist_tasks()
            return updated

    def has_running_task_for_target(self, target_id: str) -> bool:
        with self._lock:
            return any(task.target_id == target_id and task.status in {"queued", "running"} for task in self._tasks.values())

    def reconcile_incomplete_tasks(self) -> list[TaskRecord]:
        recovered: list[TaskRecord] = []
        with self._lock:
            recovered_at = utc_now()
            for task_id, task in list(self._tasks.items()):
                if task.status not in {"queued", "running"}:
                    continue
                metadata = dict(task.metadata or {})
                metadata.update(
                    {
                        "dispatch_status": "interrupted_on_startup",
                        "recovered_on_startup_at": recovered_at,
                    }
                )
                recovered_task = replace(
                    task,
                    status="failed",
                    completed_at=recovered_at,
                    error=task.error or "Task interrupted by server restart before completion.",
                    metadata=metadata,
                )
                self._tasks[task_id] = recovered_task
                recovered.append(recovered_task)

            recovered_target_ids = {task.target_id for task in recovered}
            for target_id, target in list(self._targets.items()):
                if target_id in recovered_target_ids:
                    self._targets[target_id] = replace(
                        target,
                        state="degraded",
                        last_error="Recovered interrupted task(s) during startup reconciliation.",
                        updated_at=recovered_at,
                    )
                elif target.state == "busy":
                    self._targets[target_id] = replace(target, state="idle", last_error=None, updated_at=recovered_at)

            if recovered:
                logger.warning(
                    "startup_reconciliation_completed",
                    extra={
                        "event_data": {
                            "recovered_tasks": len(recovered),
                            "task_ids": [task.task_id for task in recovered],
                        }
                    },
                )
            self._persist_targets()
            self._persist_tasks()
        return recovered

    def _load_state(self) -> None:
        targets_payload = self._read_json_file(self._targets_path)
        tasks_payload = self._read_json_file(self._tasks_path)
        if isinstance(targets_payload, list):
            for item in targets_payload:
                if isinstance(item, dict):
                    target = ExecutionTarget.from_dict(item)
                    if target.target_id:
                        self._targets[target.target_id] = target
        if isinstance(tasks_payload, list):
            for item in tasks_payload:
                if isinstance(item, dict):
                    task = TaskRecord.from_dict(item)
                    if task.task_id:
                        self._tasks[task.task_id] = task

    def _merge_targets(self, fresh_targets: dict[str, ExecutionTarget]) -> None:
        for target_id, fresh in fresh_targets.items():
            existing = self._targets.get(target_id)
            if existing is None:
                self._targets[target_id] = fresh
            else:
                self._targets[target_id] = replace(
                    fresh,
                    state=existing.state,
                    last_error=existing.last_error,
                    updated_at=existing.updated_at,
                )

    def _persist_targets(self) -> None:
        payload = [target.to_dict() for target in self._targets.values()]
        self._atomic_write_json(self._targets_path, payload)

    def _persist_tasks(self) -> None:
        payload = [task.to_dict() for task in self._tasks.values()]
        self._atomic_write_json(self._tasks_path, payload)

    @staticmethod
    def _read_json_file(path: Path) -> Any:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _atomic_write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
