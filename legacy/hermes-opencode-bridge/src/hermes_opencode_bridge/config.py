from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from .models import LaneProfile


class ConfigError(RuntimeError):
    pass


ExecutorMode = Literal["mock", "opencode"]


@dataclass(slots=True)
class AppConfig:
    host: str
    port: int
    bearer_token: str
    lane_profiles: dict[str, LaneProfile]
    executor_mode: ExecutorMode
    opencode_bin: str


ALLOWED_EXECUTORS = {"mock", "opencode"}


def _normalize_host(name: str, value: str) -> str:
    host = value.strip()
    if not host:
        raise ConfigError(f"Missing required environment variable: {name}")
    if '://' in host:
        parsed = urlsplit(host)
        host = parsed.hostname or ''
    if not host:
        raise ConfigError(f"{name} must contain a valid host or URL")
    return host


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _load_profiles(path: Path) -> dict[str, LaneProfile]:
    if not path.exists():
        raise ConfigError(f"Lane profile file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in lane profile file: {path}") from exc
    if not isinstance(raw, list) or not raw:
        raise ConfigError("Lane profile file must contain a non-empty JSON array")
    profiles: dict[str, LaneProfile] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ConfigError("Each lane profile must be a JSON object")
        profile = LaneProfile(
            lane_id=str(item.get("lane_id", "")).strip(),
            node_id=str(item.get("node_id", "")).strip(),
            hostname=str(item.get("hostname", "")).strip(),
            vm_name=str(item.get("vm_name", "")).strip(),
            ip_address=str(item.get("ip_address", "")).strip(),
            role=str(item.get("role", "")).strip() or "coding-node",
            repo_path=str(item.get("repo_path", "")).strip(),
            opencode_ready=bool(item.get("opencode_ready", False)),
            git_ready=bool(item.get("git_ready", False)),
            push_allowed=bool(item.get("push_allowed", False)),
            pull_allowed=bool(item.get("pull_allowed", False)),
            runtime_test_allowed=bool(item.get("runtime_test_allowed", False)),
            state=str(item.get("state", "idle")),
            last_error=item.get("last_error"),
        )
        if not profile.lane_id or not profile.node_id or not profile.hostname or not profile.vm_name or not profile.ip_address or not profile.repo_path:
            raise ConfigError("Lane profiles require lane_id, node_id, hostname, vm_name, ip_address, and repo_path")
        profiles[profile.lane_id] = profile
    return profiles


def load_config() -> AppConfig:
    host = _normalize_host("HERMES_BRIDGE_HOST", _require_env("HERMES_BRIDGE_HOST"))
    port = int(_require_env("HERMES_BRIDGE_PORT"))
    bearer_token = _require_env("HERMES_BRIDGE_TOKEN")
    profiles_path = Path(_require_env("HERMES_BRIDGE_LANES_FILE")).expanduser()
    lane_profiles = _load_profiles(profiles_path)
    executor_mode = _require_env("HERMES_BRIDGE_EXECUTOR")
    if executor_mode not in ALLOWED_EXECUTORS:
        raise ConfigError("HERMES_BRIDGE_EXECUTOR must be one of: mock, opencode")
    opencode_bin = _require_env("HERMES_BRIDGE_OPENCODE_BIN")
    return AppConfig(
        host=host,
        port=port,
        bearer_token=bearer_token,
        lane_profiles=lane_profiles,
        executor_mode=executor_mode,
        opencode_bin=opencode_bin,
    )
