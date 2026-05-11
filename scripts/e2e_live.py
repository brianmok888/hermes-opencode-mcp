from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from hermes_opencode_mcp.client import MCPClient, MCPClientConfig


def build_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": args.pythonpath,
            "HERMES_MCP_TARGETS_FILE": args.targets_file,
            "HERMES_MCP_EXECUTOR": "opencode",
            "HERMES_MCP_OPENCODE_BIN": args.opencode_bin,
            "HERMES_MCP_REPO_ROOT": args.repo_root,
            "HERMES_MCP_STATE_DIR": args.state_dir,
            "HERMES_MCP_LOG_LEVEL": env.get("HERMES_MCP_LOG_LEVEL", "INFO"),
            "HERMES_MCP_LOG_JSON": env.get("HERMES_MCP_LOG_JSON", "1"),
        }
    )
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Live E2E check for hermes-opencode-mcp against a real OpenCode target.")
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--text", default="Print a one-line verification summary and do not modify files.")
    parser.add_argument("--pythonpath", default=str(Path(__file__).resolve().parents[1] / "src"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--targets-file", default=os.environ.get("HERMES_MCP_TARGETS_FILE", ""))
    parser.add_argument("--state-dir", default=os.environ.get("HERMES_MCP_STATE_DIR", "/tmp/hermes-opencode-mcp-e2e-state"))
    parser.add_argument("--opencode-bin", default=os.environ.get("HERMES_MCP_OPENCODE_BIN", "opencode"))
    parser.add_argument("--wait-timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    if not args.targets_file:
        print("Missing --targets-file or HERMES_MCP_TARGETS_FILE", file=sys.stderr)
        return 2

    env = build_env(args)
    config = MCPClientConfig(
        command=sys.executable,
        args=["-m", "hermes_opencode_mcp"],
        env=env,
        cwd=args.repo_root,
        request_timeout_seconds=60,
    )
    with MCPClient(config) as client:
        health = client.health()
        result = client.submit_and_wait(
            target_id=args.target_id,
            text=args.text,
            directory=args.directory,
            wait_timeout_seconds=args.wait_timeout_seconds,
        )

    report = {
        "health": health,
        "task": {
            "task_id": result.get("task_id"),
            "status": result.get("status"),
            "summary": result.get("summary"),
            "metadata": result.get("metadata"),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
