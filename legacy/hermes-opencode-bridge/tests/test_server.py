import asyncio

from hermes_opencode_bridge.config import AppConfig
from hermes_opencode_bridge.models import LaneProfile
from hermes_opencode_bridge.server import BridgeServer


def build_server() -> BridgeServer:
    cfg = AppConfig(
        host="192.168.4.82",
        port=18097,
        bearer_token="secret-token",
        lane_profiles={
            "lane1": LaneProfile(
                lane_id="lane1",
                node_id="node1",
                hostname="node1.local",
                vm_name="vm01",
                ip_address="192.168.4.81",
                role="coding-node",
                repo_path="/tmp/repo",
                opencode_ready=True,
                git_ready=True,
                push_allowed=True,
            )
        },
        executor_mode="mock",
        opencode_bin="opencode",
    )
    return BridgeServer(cfg)


async def test_cancel_unknown_task(aiohttp_client):
    client = await aiohttp_client(build_server().app())
    resp = await client.post('/tasks/missing/cancel', headers={'Authorization': 'Bearer secret-token'})
    assert resp.status == 404
    data = await resp.json()
    assert data['error'] == 'task not found'


async def test_invalid_json_body(aiohttp_client):
    client = await aiohttp_client(build_server().app())
    resp = await client.post('/tasks', data='nope', headers={'Authorization': 'Bearer secret-token', 'Content-Type': 'application/json'})
    assert resp.status == 400
    data = await resp.json()
    assert data['error'] == 'invalid json body'


async def test_rejects_non_opencode_ready_lane(aiohttp_client):
    cfg = AppConfig(
        host="192.168.4.82",
        port=18097,
        bearer_token="secret-token",
        lane_profiles={
            "lane1": LaneProfile(
                lane_id="lane1",
                node_id="node1",
                hostname="node1.local",
                vm_name="vm01",
                ip_address="192.168.4.81",
                role="coding-node",
                repo_path="/tmp/repo",
                opencode_ready=False,
                git_ready=True,
                push_allowed=True,
            )
        },
        executor_mode="mock",
        opencode_bin="opencode",
    )
    client = await aiohttp_client(BridgeServer(cfg).app())
    resp = await client.post('/tasks', json={'lane_id': 'lane1', 'text': 'pwd', 'directory': '/tmp/repo'}, headers={'Authorization': 'Bearer secret-token'})
    assert resp.status == 409
    data = await resp.json()
    assert 'OpenCode-ready' in data['error']


async def test_mock_task_records_dispatch_metadata(aiohttp_client):
    client = await aiohttp_client(build_server().app())
    resp = await client.post('/tasks', json={'lane_id': 'lane1', 'text': 'pwd', 'directory': '/tmp/repo'}, headers={'Authorization': 'Bearer secret-token'})
    assert resp.status == 202
    data = await resp.json()
    task_id = data['task']['task_id']

    payload = None
    for _ in range(20):
        state = await client.get(f'/tasks/{task_id}', headers={'Authorization': 'Bearer secret-token'})
        payload = await state.json()
        if payload['task']['status'] == 'succeeded':
            break
        await asyncio.sleep(0.01)

    assert payload is not None
    task = payload['task']
    assert task['status'] == 'succeeded'
    assert task['metadata']['worker_prefix'] == 'oc@vm01@192.168.4.81:'
    assert task['metadata']['executor_mode'] == 'mock'
    assert task['metadata']['dispatch_status'] == 'completed'
    assert task['metadata']['execution_handle'] == f'mock:{task_id}'


async def test_cancelled_task_records_execution_handle(aiohttp_client):
    client = await aiohttp_client(build_server().app())
    resp = await client.post('/tasks', json={'lane_id': 'lane1', 'text': 'pwd', 'directory': '/tmp/repo'}, headers={'Authorization': 'Bearer secret-token'})
    assert resp.status == 202
    data = await resp.json()
    task_id = data['task']['task_id']

    cancel = await client.post(f'/tasks/{task_id}/cancel', headers={'Authorization': 'Bearer secret-token'})
    assert cancel.status == 200

    payload = None
    for _ in range(20):
        state = await client.get(f'/tasks/{task_id}', headers={'Authorization': 'Bearer secret-token'})
        payload = await state.json()
        if payload['task']['status'] == 'cancelled':
            break
        await asyncio.sleep(0.01)

    assert payload is not None
    task = payload['task']
    assert task['status'] == 'cancelled'
    assert task['metadata']['dispatch_status'] == 'cancelled_before_dispatch'
    assert task['metadata']['execution_handle'] == f'cancelled:{task_id}'
    assert task['summary'].startswith('oc@vm01@192.168.4.81:')
