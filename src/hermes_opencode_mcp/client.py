from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from .sanitizer import sanitize_text


class MCPClientError(RuntimeError):
    pass


@dataclass(slots=True)
class MCPClientConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    startup_timeout_seconds: int = 10
    request_timeout_seconds: int = 30
    poll_interval_seconds: float = 1.0


class MCPClient:
    def __init__(self, config: MCPClientConfig) -> None:
        self.config = config
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 1

    def __enter__(self) -> "MCPClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        if self._proc is not None:
            return
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
        self._proc = subprocess.Popen(
            [self.config.command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.config.cwd,
            env=env,
        )
        self.initialize()

    def close(self) -> None:
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def initialize(self) -> dict[str, Any]:
        result = self.request("initialize", {})
        self.notify("notifications/initialized", {})
        return result

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        proc = self._ensure_proc()
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        deadline = time.time() + self.config.request_timeout_seconds
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise MCPClientError(f"MCP server closed pipe unexpectedly: {sanitize_text(stderr)}")
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MCPClientError(f"invalid JSON from MCP server: {sanitize_text(line)}") from exc
            if payload.get("id") != request_id:
                continue
            if "error" in payload:
                message = payload["error"].get("message") or payload["error"]
                raise MCPClientError(sanitize_text(str(message)))
            return dict(payload.get("result") or {})
        raise MCPClientError(f"timed out waiting for MCP response to {method}")

    def health(self) -> dict[str, Any]:
        return self.call_tool("health")

    def list_targets(self) -> list[dict[str, Any]]:
        return list(self.call_tool("list_targets"))

    def get_target(self, target_id: str) -> dict[str, Any]:
        return dict(self.call_tool("get_target", {"target_id": target_id}))

    def create_task(self, *, target_id: str, text: str, directory: str, session_id: str | None = None, agent: str | None = None, timeout_ms: int = 300_000) -> dict[str, Any]:
        return dict(
            self.call_tool(
                "create_task",
                {
                    "target_id": target_id,
                    "text": text,
                    "directory": directory,
                    "session_id": session_id,
                    "agent": agent,
                    "timeout_ms": timeout_ms,
                },
            )
        )

    def submit_task(self, *, target_id: str, text: str, directory: str, session_id: str | None = None, agent: str | None = None, timeout_ms: int = 300_000) -> dict[str, Any]:
        return dict(
            self.call_tool(
                "submit_task",
                {
                    "target_id": target_id,
                    "text": text,
                    "directory": directory,
                    "session_id": session_id,
                    "agent": agent,
                    "timeout_ms": timeout_ms,
                },
            )
        )

    def run_task(self, *, target_id: str, text: str, directory: str, session_id: str | None = None, agent: str | None = None, timeout_ms: int = 300_000) -> dict[str, Any]:
        return dict(
            self.call_tool(
                "run_task",
                {
                    "target_id": target_id,
                    "text": text,
                    "directory": directory,
                    "session_id": session_id,
                    "agent": agent,
                    "timeout_ms": timeout_ms,
                },
            )
        )

    def get_task(self, task_id: str) -> dict[str, Any]:
        return dict(self.call_tool("get_task", {"task_id": task_id}))

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        return dict(self.call_tool("cancel_task", {"task_id": task_id}))

    def get_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        return list(self.call_tool("get_artifacts", {"task_id": task_id}))

    def wait_for_task(self, task_id: str, *, timeout_seconds: int = 300) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            task = self.get_task(task_id)
            if task.get("status") in {"succeeded", "failed", "cancelled"}:
                return self._sanitize_terminal_task(task)
            time.sleep(self.config.poll_interval_seconds)
        raise MCPClientError(f"timed out waiting for task {task_id}")

    def submit_and_wait(
        self,
        *,
        target_id: str,
        text: str,
        directory: str,
        session_id: str | None = None,
        agent: str | None = None,
        timeout_ms: int = 300_000,
        wait_timeout_seconds: int = 300,
        require_execution_prefix: bool = True,
        require_execution_handle: bool = True,
    ) -> dict[str, Any]:
        submitted = self.submit_task(
            target_id=target_id,
            text=text,
            directory=directory,
            session_id=session_id,
            agent=agent,
            timeout_ms=timeout_ms,
        )
        task_id = submitted.get("task_id")
        if not task_id:
            raise MCPClientError("submitted task missing task_id")
        task = self.wait_for_task(str(task_id), timeout_seconds=wait_timeout_seconds)
        return self._validate_terminal_task(
            task,
            require_execution_prefix=require_execution_prefix,
            require_execution_handle=require_execution_handle,
        )

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        return result.get("structuredContent")

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self.request("tools/list", {}).get("tools") or [])

    def list_resources(self) -> list[dict[str, Any]]:
        return list(self.request("resources/list", {}).get("resources") or [])

    def read_resource(self, uri: str) -> list[dict[str, Any]]:
        return list(self.request("resources/read", {"uri": uri}).get("contents") or [])

    def list_prompts(self) -> list[dict[str, Any]]:
        return list(self.request("prompts/list", {}).get("prompts") or [])

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict(self.request("prompts/get", {"name": name, "arguments": arguments or {}}))

    def _send(self, payload: dict[str, Any]) -> None:
        proc = self._ensure_proc()
        if proc.stdin is None:
            raise MCPClientError("MCP server stdin is unavailable")
        proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        proc.stdin.flush()

    def _ensure_proc(self) -> subprocess.Popen[str]:
        if self._proc is None:
            self.start()
        assert self._proc is not None
        return self._proc

    def _sanitize_terminal_task(self, task: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(task)
        cleaned["summary"] = sanitize_text(str(cleaned.get("summary", "")))
        if cleaned.get("error"):
            cleaned["error"] = sanitize_text(str(cleaned["error"]))
        metadata = cleaned.get("metadata")
        cleaned["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
        artifacts = cleaned.get("artifacts")
        cleaned["artifacts"] = list(artifacts) if isinstance(artifacts, list) else []
        return cleaned

    def _validate_terminal_task(
        self,
        task: dict[str, Any],
        *,
        require_execution_prefix: bool,
        require_execution_handle: bool,
    ) -> dict[str, Any]:
        metadata = task.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise MCPClientError("MCP task metadata must be an object")

        status = str(task.get("status", ""))
        if status not in {"succeeded", "failed", "cancelled"}:
            raise MCPClientError(f"MCP task did not reach terminal state: {status or 'unknown'}")

        dispatch_status = metadata.get("dispatch_status")
        if dispatch_status not in {"completed", "failed", "cancelled_before_dispatch", "cancelled_during_execution"}:
            raise MCPClientError("MCP task missing terminal dispatch_status metadata")

        if require_execution_handle and not str(metadata.get("execution_handle", "")).strip():
            raise MCPClientError("MCP task missing execution_handle metadata")

        if require_execution_prefix:
            execution_prefix = str(metadata.get("execution_prefix", "")).strip()
            if not execution_prefix:
                raise MCPClientError("MCP task missing execution_prefix metadata")
            body = str(task.get("summary") or task.get("error") or "").strip()
            if body and not body.startswith(execution_prefix):
                raise MCPClientError("MCP task output missing required execution identity prefix")

        return task
