#!/usr/bin/env python3
"""Provision legacy bridge target auth tokens during MCP migration/cleanup.

This helper was migrated from the deprecated hermes-opencode-bridge repo so the
existing bridge services can be reprovisioned, inspected, or retired cleanly
while hermes-opencode-mcp becomes the canonical implementation.

Examples:
  python3 scripts/provision-bridge-target.py vm01
  python3 scripts/provision-bridge-target.py vm02 --rotate
  python3 scripts/provision-bridge-target.py vm01 --bind-host 192.168.4.81
  python3 scripts/provision-bridge-target.py vm01 --bind-host auto
  python3 scripts/provision-bridge-target.py vm02 --detect-only
  python3 scripts/provision-bridge-target.py omniroute --restart-hermes
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import secrets
import shlex
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

HERMES_ENV = Path("/home/mok/.hermes/.env")
SSH_KEY = os.path.expanduser("~/.ssh/id_hermes")
SSH_USER = "mok"
LOCAL_GATEWAY_CMD = "cd /home/mok/.hermes/hermes-agent && exec /home/mok/.hermes/hermes-agent/.venv/bin/python -m gateway.run"
DEFAULT_PATH = "/home/mok/.bun/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


@dataclass(frozen=True)
class Target:
    name: str
    host: str
    env_key: str
    port: int
    lanes_file: str
    service_name: str
    lane_id: str
    node_id: str
    hostname: str
    vm_name: str
    ip_address: str
    role: str
    repo_path: str
    env_file: str
    bind_host: str | None = None
    local: bool = False

    @property
    def venv_bin(self) -> str:
        return f"{self.repo_path}/.venv/bin/hermes-opencode-bridge"


TARGETS: Dict[str, Target] = {
    "vm01": Target(
        name="vm01",
        host="192.168.4.81",
        env_key="HERMES_BRIDGE_VM01_TOKEN",
        port=18097,
        lanes_file="/home/mok/.hermes/vm01-bridge-lanes.json",
        service_name="hermes-opencode-bridge-vm01.service",
        lane_id="vm01-target",
        node_id="node-vm01-1",
        hostname="Coding-Space-01",
        vm_name="vm01",
        ip_address="192.168.4.81",
        role="coding-node",
        repo_path="/home/mok/projects/hermes-opencode-bridge",
        env_file="/home/mok/.env",
        bind_host="192.168.4.81",
    ),
    "vm02": Target(
        name="vm02",
        host="192.168.4.82",
        env_key="HERMES_BRIDGE_VM02_TOKEN",
        port=18097,
        lanes_file="/home/mok/.hermes/vm02-bridge-lanes.json",
        service_name="hermes-opencode-bridge-vm02.service",
        lane_id="coding-node-1",
        node_id="node-coding-1",
        hostname="Coding-Space-02",
        vm_name="vm02",
        ip_address="192.168.4.82",
        role="coding-node",
        repo_path="/home/mok/projects/hermes-opencode-bridge",
        env_file="/home/mok/.env",
        bind_host="192.168.4.82",
    ),
    "omniroute": Target(
        name="omniroute",
        host="127.0.0.1",
        env_key="HERMES_BRIDGE_OMNIROUTE_TOKEN",
        port=18097,
        lanes_file="/home/mok/.hermes/omniroute-bridge-lanes.json",
        service_name="hermes-opencode-bridge-omniroute.service",
        lane_id="omniroute-local-1",
        node_id="node-omniroute-1",
        hostname="ubuntu-vps-clean",
        vm_name="omniroute",
        ip_address="192.168.4.84",
        role="runtime-node",
        repo_path="/home/mok/projects/hermes-opencode-bridge",
        env_file="/home/mok/.hermes/.env",
        bind_host="127.0.0.1",
        local=True,
    ),
}


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def save_env(path: Path, updates: Dict[str, str]) -> None:
    lines = []
    existing = {}
    original = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.exists() else []
    for raw in original:
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in raw:
            key, _ = raw.split("=", 1)
            key = key.strip()
            if key in updates:
                lines.append(f"{key}={updates[key]}")
                existing[key] = True
                continue
        lines.append(raw)
    for key, value in updates.items():
        if key not in existing:
            lines.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def exec_target(target: Target, command: str, *, check: bool = True) -> subprocess.CompletedProcess:
    if target.local:
        return run(["bash", "-lc", command], check=check)
    return run(
        [
            "ssh",
            "-i",
            SSH_KEY,
            "-o",
            "StrictHostKeyChecking=no",
            f"{SSH_USER}@{target.host}",
            command,
        ],
        check=check,
    )


def target_env_get(target: Target, env_key: str) -> str:
    python_code = textwrap.dedent(
        f"""
from pathlib import Path
p = Path({target.env_file!r})
if not p.exists():
    raise SystemExit(0)
for raw in p.read_text(encoding='utf-8', errors='ignore').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    if k.strip() == {env_key!r}:
        print(v.strip())
        break
"""
    ).strip()
    result = exec_target(target, f"python3 -c {shlex.quote(python_code)}", check=True)
    return result.stdout.strip()


def validate_ip(ip: str, *, allow_loopback: bool) -> str:
    value = ip.strip()
    parsed = ipaddress.ip_address(value)
    if not allow_loopback and parsed.is_loopback:
        raise RuntimeError(f"loopback address not allowed for remote target: {ip}")
    return str(parsed)


def current_service_bind_host(target: Target) -> str | None:
    service_path = f"/home/mok/.config/systemd/user/{target.service_name}"
    python_code = textwrap.dedent(
        f"""
from pathlib import Path
p = Path({service_path!r})
if not p.exists():
    raise SystemExit(0)
for raw in p.read_text(encoding='utf-8', errors='ignore').splitlines():
    if raw.startswith('Environment=HERMES_BRIDGE_HOST='):
        print(raw.split('=', 2)[2].strip())
        break
"""
    ).strip()
    try:
        result = exec_target(target, f"python3 -c {shlex.quote(python_code)}", check=True)
    except Exception:
        return None
    value = result.stdout.strip()
    return value or None


def detect_remote_bind_host(target: Target) -> tuple[str, str]:
    if target.local:
        return validate_ip(target.bind_host or "127.0.0.1", allow_loopback=True), "local-default"

    detect_script = textwrap.dedent(
        f"""
python3 - <<'PY'
import json
import shutil
import socket
import subprocess

hermes_host = {target.host!r}

def emit(method, value):
    print(json.dumps({{"method": method, "value": value}}))

ip_bin = shutil.which('ip')
if ip_bin:
    try:
        p = subprocess.run([ip_bin, 'route', 'get', hermes_host], text=True, capture_output=True, check=True)
        fields = p.stdout.split()
        if 'src' in fields:
            idx = fields.index('src')
            if idx + 1 < len(fields):
                emit('ip-route-get', fields[idx + 1])
    except Exception:
        pass

hostname_i = shutil.which('hostname')
if hostname_i:
    try:
        p = subprocess.run([hostname_i, '-I'], text=True, capture_output=True, check=True)
        for part in p.stdout.split():
            emit('hostname-I', part)
    except Exception:
        pass

try:
    emit('socket-hostname', socket.gethostbyname(socket.gethostname()))
except Exception:
    pass
PY
"""
    ).strip()

    candidates: list[tuple[str, str]] = []
    try:
        result = exec_target(target, detect_script, check=True)
        for raw in result.stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            method = str(item.get("method", "unknown"))
            value = str(item.get("value", "")).strip()
            if value:
                candidates.append((method, value))
    except Exception:
        pass

    for method, value in candidates:
        try:
            return validate_ip(value, allow_loopback=False), method
        except RuntimeError:
            continue

    if target.bind_host:
        return validate_ip(target.bind_host, allow_loopback=False), "configured-fallback"
    return validate_ip(target.host, allow_loopback=False), "target-host-fallback"


def lane_payload(target: Target, bind_host: str) -> str:
    payload = [{
        "lane_id": target.lane_id,
        "node_id": target.node_id,
        "hostname": target.hostname,
        "vm_name": target.vm_name,
        "ip_address": bind_host,
        "role": target.role,
        "repo_path": target.repo_path,
        "opencode_ready": True,
        "git_ready": True,
        "push_allowed": target.role == "coding-node",
        "pull_allowed": True,
        "runtime_test_allowed": target.role == "runtime-node",
        "state": "idle",
    }]
    return json.dumps(payload, indent=2) + "\n"


def target_preflight(target: Target) -> None:
    command = textwrap.dedent(
        f"""
set -e
mkdir -p /home/mok/.config/systemd/user
mkdir -p {shlex.quote(str(Path(target.lanes_file).parent))}
test -d {shlex.quote(target.repo_path)}
test -x {shlex.quote(target.venv_bin)}
command -v opencode >/dev/null
"""
    ).strip()
    exec_target(target, command, check=True)


def target_write_env_service_and_lanes(target: Target, token: str, bind_host: str) -> None:
    service_text = textwrap.dedent(
        f"""
[Unit]
Description=Hermes OpenCode Bridge ({target.name.upper()})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={target.repo_path}
EnvironmentFile={target.env_file}
Environment=PATH={DEFAULT_PATH}
Environment=HERMES_BRIDGE_HOST={bind_host}
Environment=HERMES_BRIDGE_PORT={target.port}
Environment=HERMES_BRIDGE_LANES_FILE={target.lanes_file}
Environment=HERMES_BRIDGE_EXECUTOR=opencode
Environment=HERMES_BRIDGE_OPENCODE_BIN=opencode
ExecStart={target.venv_bin}
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
"""
    ).strip() + "\n"

    python_code = textwrap.dedent(
        f"""
from pathlib import Path

env_path = Path({target.env_file!r})
service_path = Path('/home/mok/.config/systemd/user/{target.service_name}')
lanes_path = Path({target.lanes_file!r})
env_key = {target.env_key!r}
token = {token!r}
service_text = {service_text!r}
lanes_text = {lane_payload(target, bind_host)!r}

def update_env(path: Path, key: str, value: str):
    lines = []
    found = False
    original = path.read_text(encoding='utf-8', errors='ignore').splitlines() if path.exists() else []
    for raw in original:
        stripped = raw.strip()
        if stripped and not stripped.startswith('#') and '=' in raw:
            k, _ = raw.split('=', 1)
            if k.strip() == key:
                lines.append(f'{{key}}={{value}}')
                found = True
                continue
        lines.append(raw)
    if not found:
        lines.append(f'{{key}}={{value}}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\\n'.join(lines).rstrip() + '\\n', encoding='utf-8')

update_env(env_path, env_key, token)
update_env(env_path, 'HERMES_BRIDGE_TOKEN', token)
service_path.parent.mkdir(parents=True, exist_ok=True)
service_path.write_text(service_text, encoding='utf-8')
lanes_path.parent.mkdir(parents=True, exist_ok=True)
lanes_path.write_text(lanes_text, encoding='utf-8')
"""
    ).strip()
    exec_target(target, f"python3 -c {shlex.quote(python_code)}", check=True)


def target_restart_service(target: Target) -> None:
    command = textwrap.dedent(
        f"""
set -e
systemctl --user daemon-reload
systemctl --user enable {shlex.quote(target.service_name)} >/dev/null 2>&1 || true
systemctl --user restart {shlex.quote(target.service_name)}
systemctl --user status {shlex.quote(target.service_name)} --no-pager -l | sed -n '1,30p'
"""
    ).strip()
    exec_target(target, command, check=True)


def verify_target_token(target: Target, token: str) -> None:
    actual = target_env_get(target, target.env_key)
    if actual != token:
        raise RuntimeError(f"token mismatch for {target.name}; target env was not updated correctly")


def restart_local_gateway() -> str:
    old = run(["bash", "-lc", "pgrep -f 'python -m gateway\\.run' | head -1 || true"], check=True).stdout.strip()
    if old:
        run(["bash", "-lc", f"kill {shlex.quote(old)} || true"], check=True)
        run(["bash", "-lc", textwrap.dedent(f"""
for _ in $(seq 1 120); do
  if ! kill -0 {shlex.quote(old)} 2>/dev/null; then
    break
  fi
  sleep 0.5
done
rm -f "$HOME/.local/state/hermes/gateway-locks"/*.lock 2>/dev/null || true
rm -f /home/mok/.hermes/gateway.pid 2>/dev/null || true
""")], check=True)
    proc = subprocess.Popen(
        ["bash", "-lc", f"nohup bash -lc {shlex.quote(LOCAL_GATEWAY_CMD)} >> /home/mok/.hermes/logs/gateway.log 2>&1 & echo $!"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(timeout=20)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to restart local gateway: {stderr.strip()}")
    return stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision legacy bridge targets during MCP migration")
    parser.add_argument("target", choices=sorted(TARGETS))
    parser.add_argument("--rotate", action="store_true")
    parser.add_argument("--restart-hermes", action="store_true")
    parser.add_argument("--bind-host", help="Override detected bind host with an IP, or pass 'auto' to force auto-detection")
    parser.add_argument("--detect-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = TARGETS[args.target]
    current_bind_host = current_service_bind_host(target)
    if args.bind_host and args.bind_host.strip().lower() != "auto":
        bind_host = validate_ip(args.bind_host, allow_loopback=target.local)
        bind_source = "user-override"
    else:
        bind_host, bind_source = detect_remote_bind_host(target)
        if args.bind_host and args.bind_host.strip().lower() == "auto":
            bind_source = f"explicit-auto:{bind_source}"
    would_change = "unknown"
    if current_bind_host is not None:
        would_change = "yes" if current_bind_host != bind_host else "no"
    if args.detect_only:
        print(f"target={target.name}")
        print(f"configured_bind_host={target.bind_host or ''}")
        print(f"current_service_bind_host={current_bind_host or ''}")
        print(f"bind_host={bind_host}")
        print(f"bind_source={bind_source}")
        print(f"bind_host_would_change={would_change}")
        return 0

    hermes_env = load_env(HERMES_ENV)
    local_token = hermes_env.get(target.env_key, "")
    target_token = target_env_get(target, target.env_key)
    if args.rotate:
        chosen = secrets.token_urlsafe(32)
        source = "generated (--rotate)"
    elif local_token:
        chosen = local_token
        source = "local ~/.hermes/.env"
    elif target_token:
        chosen = target_token
        source = f"target {target.env_file}"
    else:
        chosen = secrets.token_urlsafe(32)
        source = "generated"

    target_preflight(target)
    save_env(HERMES_ENV, {target.env_key: chosen})
    target_write_env_service_and_lanes(target, chosen, bind_host)
    verify_target_token(target, chosen)
    target_restart_service(target)
    gateway_pid = restart_local_gateway() if args.restart_hermes else ""

    print(f"target={target.name}")
    print(f"token_source={source}")
    print(f"env_key={target.env_key}")
    print(f"target_host={'local' if target.local else target.host}")
    print(f"target_service={target.service_name}")
    print(f"lanes_file={target.lanes_file}")
    print(f"configured_bind_host={target.bind_host or ''}")
    print(f"current_service_bind_host={current_bind_host or ''}")
    print(f"bind_host={bind_host}")
    print(f"bind_source={bind_source}")
    print(f"bind_host_changed={'yes' if current_bind_host != bind_host else 'no'}")
    print("token_synced=yes")
    if gateway_pid:
        print(f"gateway_pid={gateway_pid}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or exc.stdout or str(exc))
        raise SystemExit(exc.returncode or 1)
    except Exception as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        raise SystemExit(1)
