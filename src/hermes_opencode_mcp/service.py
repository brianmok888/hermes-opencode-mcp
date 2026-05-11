from __future__ import annotations

import asyncio
import re
from dataclasses import replace
from pathlib import Path

from .config import AppConfig
from .models import Artifact, TaskRecord, TaskRequest, new_task_id, utc_now
from .opencode_adapter import OpenCodeAdapter
from .sanitizer import sanitize_text
from .store import InMemoryStore


class ServiceError(RuntimeError):
    pass


class LaneService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = InMemoryStore(config.lane_profiles)
        self._adapter = OpenCodeAdapter(config.opencode_bin) if config.executor_mode == "opencode" else None
        if self._adapter is not None:
            self._adapter.validate()
        self._background_tasks: dict[str, asyncio.Task] = {}

    def health(self) -> dict:
        return {
            "ok": True,
            "service": self.config.server_name,
            "executor_mode": self.config.executor_mode,
        }

    def list_lanes(self) -> list[dict]:
        return [lane.to_dict() for lane in self.store.lanes()]

    def get_lane(self, lane_id: str) -> dict:
        lane = self.store.get_lane(lane_id)
        if lane is None:
            raise ServiceError(f"lane not found: {lane_id}")
        return lane.to_dict()

    def create_task(self, payload: dict) -> dict:
        request = TaskRequest.from_dict(payload)
        errors = request.validate()
        if errors:
            raise ServiceError("; ".join(errors))
        lane = self.store.get_lane(request.lane_id)
        if lane is None:
            raise ServiceError("lane not found")
        if not lane.opencode_ready:
            raise ServiceError(
                f"lane {lane.lane_id} is not OpenCode-ready; dedicated lanes must execute through their OpenCode worker only"
            )
        task = TaskRecord(
            task_id=new_task_id(),
            lane_id=request.lane_id,
            text=sanitize_text(request.text),
            directory=request.directory,
            metadata={
                "session_id": request.session_id,
                "agent": request.agent,
                "timeout_ms": request.timeout_ms,
            },
        )
        self.store.add_task(task)
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
                "uri": "resource://policy/worker",
                "name": "Worker policy",
                "description": "Hard worker/orchestrator lane policy.",
                "mimeType": "text/markdown",
            },
            {
                "uri": "resource://templates/lanes-example",
                "name": "Lane profile example",
                "description": "Example JSON lane configuration file.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str) -> dict:
        repo_root = self.config.repo_root
        if uri == "resource://architecture/overview":
            text = (
                "# Architecture\n\n"
                "Hermes resolves Telegram topic IDs to lane IDs outside this server. "
                "The MCP server then receives lane-scoped requests and executes them through the OpenCode CLI.\n"
            )
            mime = "text/markdown"
        elif uri == "resource://policy/worker":
            text = (repo_root / "WORKER_POLICY.md").read_text(encoding="utf-8")
            mime = "text/markdown"
        elif uri == "resource://templates/lanes-example":
            text = (repo_root / "templates/lanes.example.json").read_text(encoding="utf-8")
            mime = "application/json"
        else:
            raise ServiceError(f"unknown resource: {uri}")
        return {"uri": uri, "mimeType": mime, "text": text}

    def list_prompts(self) -> list[dict]:
        return [
            {
                "name": "coding-task",
                "description": "Template for code changes on a coding lane.",
                "arguments": [
                    {"name": "lane_id", "required": True},
                    {"name": "task", "required": True},
                ],
            },
            {
                "name": "runtime-check",
                "description": "Template for runtime validation on a runtime lane.",
                "arguments": [
                    {"name": "lane_id", "required": True},
                    {"name": "check", "required": True},
                ],
            },
        ]

    def get_prompt(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        if name == "coding-task":
            lane_id = arguments.get("lane_id", "<lane_id>")
            task = arguments.get("task", "<task>")
            text = f"Run this coding task on lane {lane_id}: {task}"
        elif name == "runtime-check":
            lane_id = arguments.get("lane_id", "<lane_id>")
            check = arguments.get("check", "<check>")
            text = f"Run this runtime validation on lane {lane_id}: {check}"
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
                "name": "list_lanes",
                "description": "List available OpenCode worker lanes.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "get_lane",
                "description": "Get one lane profile by lane_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"lane_id": {"type": "string"}},
                    "required": ["lane_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "create_task",
                "description": "Create a queued lane task without waiting for completion.",
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
                "description": "Create and execute a lane task, waiting for completion.",
                "inputSchema": self._task_schema(),
            },
        ]

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        if name == "health":
            result = self.health()
        elif name == "list_lanes":
            result = self.list_lanes()
        elif name == "get_lane":
            result = self.get_lane(str(arguments.get("lane_id", "")))
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
        await self._execute(task)

    async def _execute(self, task: TaskRecord) -> None:
        lane = self.store.get_lane(task.lane_id)
        if lane is None:
            failed = replace(task, status="failed", completed_at=utc_now(), error="unknown lane")
            self.store.save_task(failed)
            return

        self.store.set_lane_state(task.lane_id, "busy")
        running = replace(
            task,
            status="running",
            started_at=utc_now(),
            metadata=self._merge_metadata(
                task.metadata,
                {
                    "worker_prefix": lane.worker_prefix,
                    "executor_mode": self.config.executor_mode,
                    "dispatch_status": "running",
                    "dispatch_started_at": utc_now(),
                },
            ),
        )
        self.store.save_task(running)

        try:
            await asyncio.sleep(0.05)
            latest = self.store.get_task(running.task_id) or running
            if latest.cancel_requested:
                cancelled = replace(
                    latest,
                    status="cancelled",
                    completed_at=utc_now(),
                    summary=self._prefix_summary(lane.worker_prefix, "Task cancelled before execution adapter dispatch."),
                    metadata=self._merge_metadata(
                        latest.metadata,
                        {
                            "dispatch_status": "cancelled_before_dispatch",
                            "execution_handle": f"cancelled:{latest.task_id}",
                        },
                    ),
                )
                self.store.save_task(cancelled)
                self.store.set_lane_state(task.lane_id, "idle")
                return

            if self.config.executor_mode == "mock":
                summary = sanitize_text(
                    f"Accepted task for lane={task.lane_id} directory={task.directory}. Execution adapter not wired yet; this is the mock MCP path."
                )
                done = replace(
                    latest,
                    status="succeeded",
                    completed_at=utc_now(),
                    summary=self._prefix_summary(lane.worker_prefix, summary),
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
                        summary=self._prefix_summary(lane.worker_prefix, "Task cancelled during execution."),
                        error=self._prefix_summary(
                            lane.worker_prefix,
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
                        error=self._prefix_summary(lane.worker_prefix, sanitize_text(result.error)),
                        metadata=self._merge_metadata(
                            latest.metadata,
                            {"dispatch_status": "failed"},
                            result.metadata or {},
                        ),
                    )
                else:
                    validated_summary = self._normalize_worker_identity(lane.worker_prefix, result.summary)
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
            self.store.set_lane_state(task.lane_id, "idle")
        except Exception as exc:  # pragma: no cover
            failed = replace(
                running,
                status="failed",
                completed_at=utc_now(),
                error=self._prefix_summary(lane.worker_prefix, sanitize_text(str(exc))),
                metadata=self._merge_metadata(
                    running.metadata,
                    {"dispatch_status": "failed_before_completion"},
                ),
            )
            self.store.save_task(failed)
            self.store.set_lane_state(task.lane_id, "degraded", error=failed.error)

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
                "lane_id": {"type": "string"},
                "text": {"type": "string"},
                "directory": {"type": "string"},
                "session_id": {"type": "string"},
                "agent": {"type": "string"},
                "timeout_ms": {"type": "integer", "minimum": 1},
            },
            "required": ["lane_id", "text", "directory"],
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
    def _normalize_worker_identity(expected_prefix: str, text: str) -> str:
        stripped = sanitize_text((text or "").strip())
        if not stripped:
            return expected_prefix
        lines = stripped.splitlines()
        first_line = lines[0].strip()
        if re.match(r"^oc@[^\s:]+@[^\s:]+:\s*", first_line) and not first_line.startswith(expected_prefix):
            first_line = re.sub(r"^oc@[^\s:]+@[^\s:]+:\s*", "", first_line, count=1).strip()
            lines[0] = first_line
            stripped = "\n".join(lines).strip()
        return LaneService._prefix_summary(expected_prefix, stripped)

    @staticmethod
    def _merge_metadata(*parts: dict) -> dict:
        merged: dict = {}
        for part in parts:
            if part:
                merged.update(part)
        return merged
