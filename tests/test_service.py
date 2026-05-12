from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hermes_opencode_mcp.config import AppConfig
from hermes_opencode_mcp.models import ExecutionTarget
from hermes_opencode_mcp.service import ExecutionService, ServiceError


def build_service(tmp_path: Path) -> ExecutionService:
    target = ExecutionTarget(
        target_id="coding-node-1",
        node_id="node-1",
        hostname="vm02",
        vm_name="vm02",
        ip_address="192.168.4.82",
        role="coding-node",
        repo_path=str(tmp_path),
        opencode_ready=True,
        opencode_base_url="http://192.168.4.82:4096",
        opencode_auth_token_env="VM02_OPENCODE_TOKEN",
    )
    state_dir = tmp_path / "state"
    config = AppConfig(
        server_name="hermes-opencode-mcp",
        server_version="0.1.0",
        execution_targets={"coding-node-1": target},
        executor_mode="mock",
        opencode_bin="python3",
        repo_root=tmp_path,
        state_dir=state_dir,
        log_level="INFO",
        log_json=True,
    )
    (tmp_path / "MCP_POLICY.md").write_text("policy")
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "templates/targets.example.json").write_text("[]")
    return ExecutionService(config)


def test_health(tmp_path):
    service = build_service(tmp_path)
    health = service.health()
    assert health["ok"] is True
    assert health["running_tasks"] == 0
    assert health["targets"] == 1
    assert health["startup_recovered_tasks"] == 0


def test_list_targets(tmp_path):
    service = build_service(tmp_path)
    targets = service.list_targets()
    assert targets[0]["target_id"] == "coding-node-1"
    assert targets[0]["opencode_base_url"] == "http://192.168.4.82:4096"
    assert targets[0]["opencode_auth_token_env"] == "VM02_OPENCODE_TOKEN"


def test_run_task_mock(tmp_path):
    service = build_service(tmp_path)
    result = asyncio.run(
        service.run_task(
            {
                "target_id": "coding-node-1",
                "directory": str(tmp_path),
                "text": "say hi",
            }
        )
    )
    assert result["status"] == "succeeded"
    assert result["summary"].startswith("oc@vm02@192.168.4.82:")
    assert result["metadata"]["dispatch_status"] == "completed"
    assert result["metadata"]["execution_prefix"] == "oc@vm02@192.168.4.82:"
    assert result["artifacts"]


def test_submit_task_and_poll(tmp_path):
    service = build_service(tmp_path)

    async def run_flow():
        created = await service.submit_task(
            {
                "target_id": "coding-node-1",
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
                "target_id": "coding-node-1",
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
    result = asyncio.run(service.call_tool("get_target", {"target_id": "coding-node-1"}))
    assert result["structuredContent"]["target_id"] == "coding-node-1"


def test_reject_concurrent_task_for_same_target(tmp_path):
    service = build_service(tmp_path)
    created = service.create_task(
        {
            "target_id": "coding-node-1",
            "directory": str(tmp_path),
            "text": "queued once",
        }
    )
    assert created["status"] == "queued"
    with pytest.raises(ServiceError, match="target busy"):
        service.create_task(
            {
                "target_id": "coding-node-1",
                "directory": str(tmp_path),
                "text": "queued twice",
            }
        )


def test_persists_tasks_across_restart(tmp_path):
    service = build_service(tmp_path)
    created = service.create_task(
        {
            "target_id": "coding-node-1",
            "directory": str(tmp_path),
            "text": "persist me",
        }
    )
    rebuilt = build_service(tmp_path)
    loaded = rebuilt.get_task(created["task_id"])
    assert loaded["text"] == "persist me"
    assert loaded["status"] == "failed"
    assert loaded["metadata"]["dispatch_status"] == "interrupted_on_startup"


def test_reconciles_running_task_on_startup(tmp_path):
    service = build_service(tmp_path)
    created = service.create_task(
        {
            "target_id": "coding-node-1",
            "directory": str(tmp_path),
            "text": "recover me",
        }
    )
    task = service.store.get_task(created["task_id"])
    assert task is not None
    service.store.save_task(
        task.__class__(
            **{
                **task.to_dict(),
                "status": "running",
                "started_at": "2024-01-01T00:00:00+00:00",
            }
        )
    )
    rebuilt = build_service(tmp_path)
    loaded = rebuilt.get_task(created["task_id"])
    target = rebuilt.get_target("coding-node-1")
    assert loaded["status"] == "failed"
    assert loaded["metadata"]["dispatch_status"] == "interrupted_on_startup"
    assert target["state"] == "degraded"
