from __future__ import annotations

import asyncio
import re
from dataclasses import replace
from pathlib import Path

from .config import AppConfig
from .logging_utils import get_logger
from .models import Artifact, TaskRecord, TaskRequest, new_task_id, utc_now
from .opencode_adapter import OpenCodeAdapter
from .sanitizer import sanitize_text
from .store import PersistentStore


logger = get_logger(__name__)


class ServiceError(RuntimeError):
    pass


class ExecutionService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = PersistentStore(config.execution_targets, config.state_dir)
        self._adapter = OpenCodeAdapter(config.opencode_bin) if config.executor_mode == "opencode" else None
        if self._adapter is not None:
            self._adapter.validate()
        self._background_tasks: dict[str, asyncio.Task] = {}
        self._startup_recovered_tasks = self.store.reconcile_incomplete_tasks()
        if self._startup_recovered_tasks:
            logger.warning(
                "service_recovered_interrupted_tasks",
                extra={"event_data": {"recovered_tasks": len(self._startup_recovered_tasks)}},
            )

    def health(self) -> dict:
        running_tasks = 0
        for target in self.store.targets():
            if target.state == "busy":
                running_tasks += 1
        return {
            "ok": True,
            "service": self.config.server_name,
            "executor_mode": self.config.executor_mode,
            "state_dir": str(self.config.state_dir),
            "targets": len(self.store.targets()),
            "running_tasks": running_tasks,
            "startup_recovered_tasks": len(self._startup_recovered_tasks),
        }

    def list_targets(self) -> list[dict]:
        return [target.to_dict() for target in self.store.targets()]

    def get_target(self, target_id: str) -> dict:
        target = self.store.get_target(target_id)
        if target is None:
            raise ServiceError(f"target not found: {target_id}")
        return target.to_dict()

    def create_task(self, payload: dict) -> dict:
        request = TaskRequest.from_dict(payload)
        errors = request.validate()
        if errors:
            raise ServiceError("; ".join(errors))
        target = self.store.get_target(request.target_id)
        if target is None:
            raise ServiceError("target not found")
        if not target.opencode_ready:
            raise ServiceError(
                f"target {target.target_id} is not OpenCode-ready for MCP execution"
            )
        if self.store.has_running_task_for_target(request.target_id):
            raise ServiceError(f"target busy: {request.target_id}")
        task = TaskRecord(
            task_id=new_task_id(),
            target_id=request.target_id,
            text=sanitize_text(request.text),
            directory=request.directory,
            metadata={
                "session_id": request.session_id,
                "agent": request.agent,
                "timeout_ms": request.timeout_ms,
            },
        )
        self.store.add_task(task)
        logger.info(
            "task_created",
            extra={
                "event_data": {
                    "task_id": task.task_id,
                    "target_id": task.target_id,
                    "directory": task.directory,
                    "text_length": len(task.text),
                }
            },
        )
        return task.to_dict()

    async def submit_task(self, payload: dict) -> dict:
        task = self.create_task(payload)
        task_id = str(task["task_id"])
        background = asyncio.create_task(self._dispatch_task(task_id))
        self._background_tasks[task_id] = background
        background.add_done_callback(lambda _: self._background_tasks.pop(task_id, None))
        return self.get_task(task_id)

    async def dispatch_task(self, task_id: str) -> dict:
        await self._dispatch_task(task_id)
        latest = self.store.get_task(task_id)
        assert latest is not None
        return latest.to_dict()

    async def run_task(self, payload: dict) -> dict:
        task = self.create_task(payload)
        return await self.dispatch_task(task["task_id"])

    def get_task(self, task_id: str) -> dict:
        task = self.store.get_task(task_id)
        if task is None:
            raise ServiceError("task not found")
        return task.to_dict()

    def cancel_task(self, task_id: str) -> dict:
        task = self.store.request_cancel(task_id)
        if task is None:
            raise ServiceError("task not found")
        logger.info(
            "task_cancel_requested",
            extra={"event_data": {"task_id": task_id, "status": task.status, "target_id": task.target_id}},
        )
        return task.to_dict()

    def get_artifacts(self, task_id: str) -> list[dict]:
        task = self.store.get_task(task_id)
        if task is None:
            raise ServiceError("task not found")
        return [artifact.to_dict() for artifact in task.artifacts]

    def list_resources(self) -> list[dict]:
        return [
            {
                "uri": "resource://architecture/overview",
                "name": "Architecture overview",
                "description": "High-level description of the MCP CLI-first architecture.",
                "mimeType": "text/markdown",
            },
            {
                "uri": "resource://policy/execution",
                "name": "Execution policy",
                "description": "Hard MCP execution target policy.",
                "mimeType": "text/markdown",
            },
            {
                "uri": "resource://templates/targets-example",
                "name": "Execution target example",
                "description": "Example JSON execution target configuration file.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str) -> dict:
        repo_root = self.config.repo_root
        if uri == "resource://architecture/overview":
            text = (
                "# Architecture\n\n"
                "The MCP server receives target-scoped requests from an MCP client and executes them through the OpenCode CLI.\n"
            )
            mime = "text/markdown"
        elif uri == "resource://policy/execution":
            text = (repo_root / "MCP_POLICY.md").read_text(encoding="utf-8")
            mime = "text/markdown"
        elif uri == "resource://templates/targets-example":
            text = (repo_root / "templates/targets.example.json").read_text(encoding="utf-8")
            mime = "application/json"
        else:
            raise ServiceError(f"unknown resource: {uri}")
        return {"uri": uri, "mimeType": mime, "text": text}

    def list_prompts(self) -> list[dict]:
        return [
            {
                "name": "coding-task",
                "description": "Template for code changes on a coding target.",
                "arguments": [
                    {"name": "target_id", "required": True},
                    {"name": "task", "required": True},
                ],
            },
            {
                "name": "runtime-check",
                "description": "Template for runtime validation on a runtime target.",
                "arguments": [
                    {"name": "target_id", "required": True},
                    {"name": "check", "required": True},
                ],
            },
        ]

    def get_prompt(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        if name == "coding-task":
            target_id = arguments.get("target_id", "<target_id>")
            task = arguments.get("task", "<task>")
            text = f"Run this coding task on target {target_id}: {task}"
        elif name == "runtime-check":
            target_id = arguments.get("target_id", "<target_id>")
            check = arguments.get("check", "<check>")
            text = f"Run this runtime validation on target {target_id}: {check}"
        else:
            raise ServiceError(f"unknown prompt: {name}")
        return {"name": name, "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}

    def tools_schema(self) -> list[dict]:
        return [
            {
                "name": "health",
                "description": "Return basic server health and executor mode.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "list_targets",
                "description": "List available OpenCode execution targets.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "get_target",
                "description": "Get one execution target by target_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"target_id": {"type": "string"}},
                    "required": ["target_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "create_task",
                "description": "Create a queued execution task without waiting for completion.",
                "inputSchema": self._task_schema(),
            },
            {
                "name": "submit_task",
                "description": "Create a task and start background execution immediately.",
                "inputSchema": self._task_schema(),
            },
            {
                "name": "get_task",
                "description": "Get a task by task_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "cancel_task",
                "description": "Request cancellation for a task by task_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "get_artifacts",
                "description": "List artifacts attached to a task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "run_task",
                "description": "Create and execute an execution task, waiting for completion.",
                "inputSchema": self._task_schema(),
            },
        ]

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        if name == "health":
            result = self.health()
        elif name == "list_targets":
            result = self.list_targets()
        elif name == "get_target":
            result = self.get_target(str(arguments.get("target_id", "")))
        elif name == "create_task":
            result = self.create_task(arguments)
        elif name == "submit_task":
            result = await self.submit_task(arguments)
        elif name == "get_task":
            result = self.get_task(str(arguments.get("task_id", "")))
        elif name == "cancel_task":
            result = self.cancel_task(str(arguments.get("task_id", "")))
        elif name == "get_artifacts":
            result = self.get_artifacts(str(arguments.get("task_id", "")))
        elif name == "run_task":
            result = await self.run_task(arguments)
        else:
            raise ServiceError(f"unknown tool: {name}")
        return {"content": [{"type": "text", "text": sanitize_text(str(result))}], "structuredContent": result}

    async def _dispatch_task(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            raise ServiceError("task not found")
        logger.info("task_dispatch_requested", extra={"event_data": {"task_id": task_id, "target_id": task.target_id}})
        await self._execute(task)

    async def _execute(self, task: TaskRecord) -> None:
        target = self.store.get_target(task.target_id)
        if target is None:
            failed = replace(task, status="failed", completed_at=utc_now(), error="unknown target")
            self.store.save_task(failed)
            return

        self.store.set_target_state(task.target_id, "busy")
        running = replace(
            task,
            status="running",
            started_at=utc_now(),
            metadata=self._merge_metadata(
                task.metadata,
                {
                    "execution_prefix": target.execution_prefix,
                    "executor_mode": self.config.executor_mode,
                    "dispatch_status": "running",
                    "dispatch_started_at": utc_now(),
                },
            ),
        )
        self.store.save_task(running)
        logger.info(
            "task_running",
            extra={"event_data": {"task_id": running.task_id, "target_id": running.target_id, "executor_mode": self.config.executor_mode}},
        )

        try:
            await asyncio.sleep(0.05)
            latest = self.store.get_task(running.task_id) or running
            if latest.cancel_requested:
                cancelled = replace(
                    latest,
                    status="cancelled",
                    completed_at=utc_now(),
                    summary=self._prefix_summary(target.execution_prefix, "Task cancelled before execution adapter dispatch."),
                    metadata=self._merge_metadata(
                        latest.metadata,
                        {
                            "dispatch_status": "cancelled_before_dispatch",
                            "execution_handle": f"cancelled:{latest.task_id}",
                        },
                    ),
                )
                self.store.save_task(cancelled)
                self.store.set_target_state(task.target_id, "idle")
                logger.info(
                    "task_cancelled_before_dispatch",
                    extra={"event_data": {"task_id": latest.task_id, "target_id": latest.target_id}},
                )
                return

            if self.config.executor_mode == "mock":
                summary = sanitize_text(
                    f"Accepted task for target={task.target_id} directory={task.directory}. Execution adapter not wired yet; this is the mock MCP path."
                )
                done = replace(
                    latest,
                    status="succeeded",
                    completed_at=utc_now(),
                    summary=self._prefix_summary(target.execution_prefix, summary),
                    metadata=self._merge_metadata(
                        latest.metadata,
                        {
                            "dispatch_status": "completed",
                            "execution_handle": f"mock:{latest.task_id}",
                        },
                    ),
                    artifacts=self._mock_artifacts(latest),
                )
            else:
                assert self._adapter is not None
                result = await self._adapter.run(
                    text=latest.text,
                    directory=latest.directory,
                    agent=latest.metadata.get("agent"),
                    session_id=latest.metadata.get("session_id"),
                    timeout_ms=int(latest.metadata.get("timeout_ms", 300000)),
                    cancel_check=lambda: bool((self.store.get_task(latest.task_id) or latest).cancel_requested),
                )
                if result.cancelled:
                    done = replace(
                        latest,
                        status="cancelled",
                        completed_at=utc_now(),
                        summary=self._prefix_summary(target.execution_prefix, "Task cancelled during execution."),
                        error=self._prefix_summary(
                            target.execution_prefix,
                            sanitize_text(result.error or "opencode execution cancelled during execution"),
                        ),
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {"dispatch_status": "cancelled_during_execution"},
                            result.metadata or {},
                        ),
                    )
                elif result.error:
                    done = replace(
                        latest,
                        status="failed",
                        completed_at=utc_now(),
                        error=self._prefix_summary(target.execution_prefix, sanitize_text(result.error)),
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {"dispatch_status": "failed"},
                            result.metadata or {},
                        ),
                    )
                else:
                    validated_summary = self._normalize_execution_identity(target.execution_prefix, result.summary)
                    done = replace(
                        latest,
                        status="succeeded",
                        completed_at=utc_now(),
                        summary=validated_summary,
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {"dispatch_status": "completed"},
                            result.metadata or {},
                        ),
                    )
            self.store.save_task(done)
            self.store.set_target_state(task.target_id, "idle")
            logger.info(
                "task_terminal",
                extra={
                    "event_data": {
                        "task_id": done.task_id,
                        "target_id": done.target_id,
                        "status": done.status,
                        "dispatch_status": (done.metadata or {}).get("dispatch_status"),
                        "execution_handle": (done.metadata or {}).get("execution_handle"),
                        "summary_length": len(done.summary or ""),
                        "error_present": bool(done.error),
                    }
                },
            )
        except Exception as exc:  # pragma: no cover
            failed = replace(
                running,
                status="failed",
                completed_at=utc_now(),
                error=self._prefix_summary(target.execution_prefix, sanitize_text(str(exc))),
                metadata=self._merge_metadata(
                    running.metadata,
                    {"dispatch_status": "failed_before_completion"},
                ),
            )
            self.store.save_task(failed)
            self.store.set_target_state(task.target_id, "degraded", error=failed.error)
            logger.exception(
                "task_execution_failed_unhandled",
                extra={"event_data": {"task_id": running.task_id, "target_id": running.target_id}},
            )

    @staticmethod
    def _mock_artifacts(task: TaskRecord) -> list[Artifact]:
        output_path = Path(task.directory) / f"{task.task_id}.summary.txt"
        return [
            Artifact(
                artifact_id=f"artifact_{task.task_id}",
                filename=output_path.name,
                path=str(output_path),
                mime_type="text/plain",
                safe_to_forward=True,
            )
        ]

    @staticmethod
    def _task_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "target_id": {"type": "string"},
                "text": {"type": "string"},
                "directory": {"type": "string"},
                "session_id": {"type": "string"},
                "agent": {"type": "string"},
                "timeout_ms": {"type": "integer", "minimum": 1},
            },
            "required": ["target_id", "text", "directory"],
            "additionalProperties": False,
        }

    @staticmethod
    def _prefix_summary(prefix: str, text: str) -> str:
        stripped = (text or "").strip()
        if not stripped:
            return prefix
        if stripped.startswith(prefix):
            return stripped
        return f"{prefix} {stripped}"

    @staticmethod
    def _normalize_execution_identity(expected_prefix: str, text: str) -> str:
        stripped = sanitize_text((text or "").strip())
        if not stripped:
            return expected_prefix
        lines = stripped.splitlines()
        first_line = lines[0].strip()
        if re.match(r"^oc@[^\s:]+@[^\s:]+:\s*", first_line) and not first_line.startswith(expected_prefix):
            first_line = re.sub(r"^oc@[^\s:]+@[^\s:]+:\s*", "", first_line, count=1).strip()
            lines[0] = first_line
            stripped = "\n".join(lines).strip()
        return ExecutionService._prefix_summary(expected_prefix, stripped)

    @staticmethod
    def _merge_metadata(*parts: dict) -> dict:
        merged: dict = {}
        for part in parts:
            if part:
                merged.update(part)
        return merged
