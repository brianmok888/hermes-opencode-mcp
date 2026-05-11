from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

TargetState = Literal["idle", "busy", "degraded", "offline"]
TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
NodeRole = Literal["coding-node", "runtime-node", "mixed-node"]
Sensitivity = Literal["safe", "metadata-only", "sensitive"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Artifact:
    artifact_id: str
    filename: str
    path: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    created_at: str = field(default_factory=utc_now)
    sensitivity: Sensitivity = "metadata-only"
    safe_to_forward: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Artifact":
        return cls(
            artifact_id=str(payload.get("artifact_id", "")).strip(),
            filename=str(payload.get("filename", "")).strip(),
            path=str(payload.get("path", "")).strip(),
            mime_type=str(payload.get("mime_type", "application/octet-stream")).strip() or "application/octet-stream",
            size_bytes=int(payload.get("size_bytes", 0)),
            created_at=str(payload.get("created_at", utc_now())),
            sensitivity=str(payload.get("sensitivity", "metadata-only")),
            safe_to_forward=bool(payload.get("safe_to_forward", False)),
        )


@dataclass(slots=True)
class ExecutionTarget:
    target_id: str
    node_id: str
    hostname: str
    vm_name: str
    ip_address: str
    role: NodeRole
    repo_path: str
    opencode_ready: bool = False
    git_ready: bool = False
    push_allowed: bool = False
    pull_allowed: bool = False
    runtime_test_allowed: bool = False
    state: TargetState = "idle"
    last_error: str | None = None
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExecutionTarget":
        return cls(
            target_id=str(payload.get("target_id", "")).strip(),
            node_id=str(payload.get("node_id", "")).strip(),
            hostname=str(payload.get("hostname", "")).strip(),
            vm_name=str(payload.get("vm_name", "")).strip(),
            ip_address=str(payload.get("ip_address", "")).strip(),
            role=str(payload.get("role", "coding-node")) or "coding-node",
            repo_path=str(payload.get("repo_path", "")).strip(),
            opencode_ready=bool(payload.get("opencode_ready", False)),
            git_ready=bool(payload.get("git_ready", False)),
            push_allowed=bool(payload.get("push_allowed", False)),
            pull_allowed=bool(payload.get("pull_allowed", False)),
            runtime_test_allowed=bool(payload.get("runtime_test_allowed", False)),
            state=str(payload.get("state", "idle")),
            last_error=payload.get("last_error"),
            updated_at=str(payload.get("updated_at", utc_now())),
        )

    @property
    def execution_prefix(self) -> str:
        return f"oc@{self.vm_name}@{self.ip_address}:"


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    target_id: str
    text: str
    directory: str
    status: TaskStatus = "queued"
    submitted_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    summary: str = ""
    error: str | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        return data

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskRecord":
        artifacts = payload.get("artifacts") or []
        return cls(
            task_id=str(payload.get("task_id", "")).strip(),
            target_id=str(payload.get("target_id", "")).strip(),
            text=str(payload.get("text", "")),
            directory=str(payload.get("directory", "")).strip(),
            status=str(payload.get("status", "queued")),
            submitted_at=str(payload.get("submitted_at", utc_now())),
            started_at=(str(payload.get("started_at")) if payload.get("started_at") else None),
            completed_at=(str(payload.get("completed_at")) if payload.get("completed_at") else None),
            summary=str(payload.get("summary", "")),
            error=(str(payload.get("error")) if payload.get("error") is not None else None),
            artifacts=[Artifact.from_dict(item) for item in artifacts if isinstance(item, dict)],
            metadata=dict(payload.get("metadata") or {}),
            cancel_requested=bool(payload.get("cancel_requested", False)),
        )


@dataclass(slots=True)
class TaskRequest:
    target_id: str
    text: str
    directory: str
    session_id: str | None = None
    agent: str | None = None
    timeout_ms: int = 300_000

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskRequest":
        return cls(
            target_id=str(payload.get("target_id", "")).strip(),
            text=str(payload.get("text", "")).strip(),
            directory=str(payload.get("directory", "")).strip(),
            session_id=(str(payload.get("session_id")).strip() if payload.get("session_id") else None),
            agent=(str(payload.get("agent")).strip() if payload.get("agent") else None),
            timeout_ms=int(payload.get("timeout_ms", 300_000)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.target_id:
            errors.append("target_id is required")
        if not self.text:
            errors.append("text is required")
        if not self.directory:
            errors.append("directory is required")
        if self.timeout_ms <= 0:
            errors.append("timeout_ms must be > 0")
        if len(self.text) > 20000:
            errors.append("text exceeds 20000 characters")
        return errors


def new_task_id() -> str:
    return f"task_{uuid4().hex[:12]}"
