from __future__ import annotations

import json
from pathlib import Path

from hermes_opencode_mcp.client import MCPClient, MCPClientConfig


def test_client_end_to_end(tmp_path: Path):
    lanes = tmp_path / "lanes.json"
    lanes.write_text(
        json.dumps(
            [
                {
                    "lane_id": "coding-node-1",
                    "node_id": "node-1",
                    "hostname": "vm02",
                    "vm_name": "vm02",
                    "ip_address": "192.168.4.82",
                    "role": "coding-node",
                    "repo_path": str(tmp_path),
                    "opencode_ready": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    env = {
        "PYTHONPATH": "/home/mok/projects/hermes-opencode-mcp/src",
        "HERMES_MCP_LANES_FILE": str(lanes),
        "HERMES_MCP_EXECUTOR": "mock",
        "HERMES_MCP_OPENCODE_BIN": "python3",
        "HERMES_MCP_REPO_ROOT": str(tmp_path),
    }
    (tmp_path / "WORKER_POLICY.md").write_text("policy", encoding="utf-8")
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "templates/lanes.example.json").write_text("[]", encoding="utf-8")

    with MCPClient(MCPClientConfig(command="python3", args=["-m", "hermes_opencode_mcp"], env=env, cwd="/home/mok/projects/hermes-opencode-mcp")) as client:
        health = client.health()
        assert health["ok"] is True
        lane = client.get_lane("coding-node-1")
        assert lane["vm_name"] == "vm02"
        result = client.run_task(lane_id="coding-node-1", text="say hi", directory=str(tmp_path))
        assert result["status"] == "succeeded"
        assert result["summary"].startswith("oc@vm02@192.168.4.82:")
