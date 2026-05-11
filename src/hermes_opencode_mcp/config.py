from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .models import ExecutionTarget


class ConfigError(RuntimeError):
    pass


ExecutorMode = Literal["mock", "opencode"]


@dataclass(slots=True)
class AppConfig:
    server_name: str
    server_version: str
    execution_targets: dict[str, ExecutionTarget]
    executor_mode: ExecutorMode
    opencode_bin: str
    repo_root: Path
    state_dir: Path
    log_level: str
    log_json: bool


ALLOWED_EXECUTORS = {"mock", "opencode"}
ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _load_targets(path: Path) -> dict[str, ExecutionTarget]:
    if not path.exists():
        raise ConfigError(f"Execution target file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in execution target file: {path}") from exc
    if not isinstance(raw, list) or not raw:
        raise ConfigError("Execution target file must contain a non-empty JSON array")
    targets: dict[str, ExecutionTarget] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigError("Each execution target must be a JSON object")
        target = ExecutionTarget.from_dict(item)
        if not target.target_id or not target.node_id or not target.hostname or not target.vm_name or not target.ip_address or not target.repo_path:
            raise ConfigError("Execution targets require target_id, node_id, hostname, vm_name, ip_address, and repo_path")
        targets[target.target_id] = target
    return targets


def _prepare_state_dir(raw_path: str) -> Path:
    state_dir = Path(raw_path).expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    if not state_dir.is_dir():
        raise ConfigError(f"State directory is not a directory: {state_dir}")
    return state_dir


def _load_log_level() -> str:
    value = os.getenv("HERMES_MCP_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if value not in ALLOWED_LOG_LEVELS:
        raise ConfigError("HERMES_MCP_LOG_LEVEL must be one of: CRITICAL, ERROR, WARNING, INFO, DEBUG")
    return value


def _load_log_json() -> bool:
    value = os.getenv("HERMES_MCP_LOG_JSON", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def load_config() -> AppConfig:
    targets_path = Path(_require_env("HERMES_MCP_TARGETS_FILE")).expanduser()
    execution_targets = _load_targets(targets_path)
    executor_mode = _require_env("HERMES_MCP_EXECUTOR")
    if executor_mode not in ALLOWED_EXECUTORS:
        raise ConfigError("HERMES_MCP_EXECUTOR must be one of: mock, opencode")
    opencode_bin = _require_env("HERMES_MCP_OPENCODE_BIN")
    repo_root = Path(_require_env("HERMES_MCP_REPO_ROOT")).expanduser()
    state_dir = _prepare_state_dir(_require_env("HERMES_MCP_STATE_DIR"))
    return AppConfig(
        server_name=os.getenv("HERMES_MCP_SERVER_NAME", "hermes-opencode-mcp").strip() or "hermes-opencode-mcp",
        server_version=os.getenv("HERMES_MCP_SERVER_VERSION", "0.1.0").strip() or "0.1.0",
        execution_targets=execution_targets,
        executor_mode=executor_mode,
        opencode_bin=opencode_bin,
        repo_root=repo_root,
        state_dir=state_dir,
        log_level=_load_log_level(),
        log_json=_load_log_json(),
    )
