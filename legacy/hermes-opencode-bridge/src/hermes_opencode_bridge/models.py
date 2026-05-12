from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

LaneState = Literal["idle", "busy", "degraded", "offline"]
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

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class LaneProfile:
    lane_id: str
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
    state: LaneState = "idle"
    last_error: str | None = None
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def worker_prefix(self) -> str:
        return f"oc@{self.vm_name}@{self.ip_address}:"


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    lane_id: str
    text: str
    directory: str
    status: TaskStatus = "queued"
    submitted_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    summary: str = ""
    error: str | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    cancel_requested: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        return data


@dataclass(slots=True)
class TaskRequest:
    lane_id: str
    text: str
    directory: str
    session_id: str | None = None
    agent: str | None = None
    timeout_ms: int = 300_000

    @classmethod
    def from_payload(cls, payload: dict) -> "TaskRequest":
        return cls(
            lane_id=str(payload.get("lane_id", "")).strip(),
            text=str(payload.get("text", "")).strip(),
            directory=str(payload.get("directory", "")).strip(),
            session_id=(str(payload.get("session_id")).strip() if payload.get("session_id") else None),
            agent=(str(payload.get("agent")).strip() if payload.get("agent") else None),
            timeout_ms=int(payload.get("timeout_ms", 300_000)),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.lane_id:
            errors.append("lane_id is required")
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
