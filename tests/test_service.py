from __future__ import annotations

import asyncio
from pathlib import Path

from hermes_opencode_mcp.config import AppConfig
from hermes_opencode_mcp.models import LaneProfile
from hermes_opencode_mcp.service import LaneService


def build_service(tmp_path: Path) -> LaneService:
    lane = LaneProfile(
        lane_id="coding-node-1",
        node_id="node-1",
        hostname="vm02",
        vm_name="vm02",
        ip_address="192.168.4.82",
        role="coding-node",
        repo_path=str(tmp_path),
        opencode_ready=True,
    )
    config = AppConfig(
        server_name="hermes-opencode-mcp",
        server_version="0.1.0",
        lane_profiles={"coding-node-1": lane},
        executor_mode="mock",
        opencode_bin="python3",
        repo_root=tmp_path,
    )
    (tmp_path / "WORKER_POLICY.md").write_text("policy")
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "templates/lanes.example.json").write_text("[]")
    return LaneService(config)


def test_health(tmp_path):
    service = build_service(tmp_path)
    assert service.health()["ok"] is True


def test_list_lanes(tmp_path):
    service = build_service(tmp_path)
    lanes = service.list_lanes()
    assert lanes[0]["lane_id"] == "coding-node-1"


def test_run_task_mock(tmp_path):
    service = build_service(tmp_path)
    result = asyncio.run(
        service.run_task(
            {
                "lane_id": "coding-node-1",
                "directory": str(tmp_path),
                "text": "say hi",
            }
        )
    )
    assert result["status"] == "succeeded"
    assert result["summary"].startswith("oc@vm02@192.168.4.82:")
    assert result["metadata"]["dispatch_status"] == "completed"
    assert result["artifacts"]


def test_submit_task_and_poll(tmp_path):
    service = build_service(tmp_path)

    async def run_flow():
        created = await service.submit_task(
            {
                "lane_id": "coding-node-1",
                "directory": str(tmp_path),
                "text": "say hi async",
            }
        )
        task_id = created["task_id"]
        for _ in range(20):
            polled = service.get_task(task_id)
            if polled["status"] in {"succeeded", "failed", "cancelled"}:
                return polled
            await asyncio.sleep(0.02)
        return service.get_task(task_id)

    result = asyncio.run(run_flow())
    assert result["status"] == "succeeded"


def test_get_artifacts(tmp_path):
    service = build_service(tmp_path)
    result = asyncio.run(
        service.run_task(
            {
                "lane_id": "coding-node-1",
                "directory": str(tmp_path),
                "text": "artifact check",
            }
        )
    )
    artifacts = service.get_artifacts(result["task_id"])
    assert len(artifacts) == 1
    assert artifacts[0]["mime_type"] == "text/plain"


def test_tools_call_returns_structured_content(tmp_path):
    service = build_service(tmp_path)
    result = asyncio.run(service.call_tool("get_lane", {"lane_id": "coding-node-1"}))
    assert result["structuredContent"]["lane_id"] == "coding-node-1"
