from __future__ import annotations

import json
from pathlib import Path

from hermes_opencode_mcp.client import MCPClient, MCPClientConfig


def test_client_end_to_end(tmp_path: Path):
    targets = tmp_path / "targets.json"
    state_dir = tmp_path / "state"
    targets.write_text(
        json.dumps(
            [
                {
                    "target_id": "coding-node-1",
                    "node_id": "node-1",
                    "hostname": "vm02",
                    "vm_name": "vm02",
                    "ip_address": "192.168.4.82",
                    "role": "coding-node",
                    "repo_path": str(tmp_path),
                    "opencode_ready": True,
                    "opencode_base_url": "http://192.168.4.82:4096",
                    "opencode_auth_token_env": "VM02_OPENCODE_TOKEN",
                }
            ]
        ),
        encoding="utf-8",
    )
    env = {
        "PYTHONPATH": "/home/mok/projects/hermes-opencode-mcp/src",
        "HERMES_MCP_TARGETS_FILE": str(targets),
        "HERMES_MCP_EXECUTOR": "mock",
        "HERMES_MCP_OPENCODE_BIN": "python3",
        "HERMES_MCP_REPO_ROOT": str(tmp_path),
        "HERMES_MCP_STATE_DIR": str(state_dir),
        "HERMES_MCP_LOG_LEVEL": "INFO",
        "HERMES_MCP_LOG_JSON": "1",
    }
    (tmp_path / "MCP_POLICY.md").write_text("policy", encoding="utf-8")
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "templates/targets.example.json").write_text("[]", encoding="utf-8")

    with MCPClient(MCPClientConfig(command="python3", args=["-m", "hermes_opencode_mcp"], env=env, cwd="/home/mok/projects/hermes-opencode-mcp")) as client:
        health = client.health()
        assert health["ok"] is True
        assert health["state_dir"] == str(state_dir)
        target = client.get_target("coding-node-1")
        assert target["vm_name"] == "vm02"
        assert target["opencode_base_url"] == "http://192.168.4.82:4096"
        assert target["opencode_auth_token_env"] == "VM02_OPENCODE_TOKEN"
        result = client.run_task(target_id="coding-node-1", text="say hi", directory=str(tmp_path))
        assert result["status"] == "succeeded"
        assert result["summary"].startswith("oc@vm02@192.168.4.82:")
