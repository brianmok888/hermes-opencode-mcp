import asyncio
from dataclasses import replace

from hermes_opencode_bridge.config import AppConfig
from hermes_opencode_bridge.executor import TaskExecutor
from hermes_opencode_bridge.models import LaneProfile, TaskRecord
from hermes_opencode_bridge.opencode_adapter import AdapterResult
from hermes_opencode_bridge.store import InMemoryStore


class FakeAdapter:
    def __init__(self, result: AdapterResult, on_run=None) -> None:
        self.result = result
        self.on_run = on_run

    def validate(self) -> None:
        return None

    async def run(self, **kwargs) -> AdapterResult:
        if self.on_run is not None:
            await self.on_run(kwargs)
        return self.result


def build_executor(result: AdapterResult, *, on_run=None) -> tuple[TaskExecutor, InMemoryStore, TaskRecord]:
    lane = LaneProfile(
        lane_id='lane1',
        node_id='node1',
        hostname='node1.local',
        vm_name='vm01',
        ip_address='192.168.4.81',
        role='coding-node',
        repo_path='/tmp/repo',
        opencode_ready=True,
        git_ready=True,
        push_allowed=True,
    )
    config = AppConfig(
        host='192.168.4.82',
        port=18097,
        bearer_token='secret-token',
        lane_profiles={'lane1': lane},
        executor_mode='opencode',
        opencode_bin='python3',
    )
    store = InMemoryStore(config.lane_profiles)
    executor = TaskExecutor(store, config)
    executor._adapter = FakeAdapter(result, on_run=on_run)  # type: ignore[attr-defined]
    task = TaskRecord(task_id='task_123', lane_id='lane1', text='pwd', directory='/tmp/repo')
    store.add_task(task)
    return executor, store, task


def test_execute_marks_cancelled_during_execution() -> None:
    async def on_run(kwargs) -> None:
        current = store.get_task('task_123')
        assert current is not None
        store.save_task(replace(current, cancel_requested=True))
        await asyncio.sleep(0)

    result = AdapterResult(
        summary='',
        error='opencode execution cancelled during execution',
        metadata={'execution_handle': 'pid:123', 'return_code': -9, 'cancelled': True},
        cancelled=True,
    )
    executor, store, task = build_executor(result, on_run=on_run)

    asyncio.run(executor.execute(task))

    final = store.get_task('task_123')
    assert final is not None
    assert final.status == 'cancelled'
    assert final.metadata['dispatch_status'] == 'cancelled_during_execution'
    assert final.metadata['execution_handle'] == 'pid:123'
    assert final.summary.startswith('oc@vm01@192.168.4.81:')
    assert final.error.startswith('oc@vm01@192.168.4.81:')


def test_execute_passes_cancel_check_to_adapter() -> None:
    seen = {}

    async def on_run(kwargs) -> None:
        seen['cancel_check_result'] = kwargs['cancel_check']()

    result = AdapterResult(summary='done', metadata={'execution_handle': 'session:ses_1', 'return_code': 0})
    executor, store, task = build_executor(result, on_run=on_run)

    asyncio.run(executor.execute(task))

    assert seen['cancel_check_result'] is False


def test_normalize_worker_identity_rewrites_wrong_prefix() -> None:
    normalized = TaskExecutor._normalize_worker_identity(
        'oc@omniroute@192.168.4.84:',
        'oc@vm02@192.168.4.82: worker=oc@vm02@192.168.4.82:\nhostname=ubuntu-vps-clean\nip=192.168.4.84',
    )

    assert normalized.startswith('oc@omniroute@192.168.4.84:')
    assert 'oc@vm02@192.168.4.82: worker=' not in normalized
    assert 'worker=oc@vm02@192.168.4.82:' in normalized


def test_execute_rewrites_mismatched_worker_prefix_from_adapter_summary() -> None:
    result = AdapterResult(
        summary='oc@vm02@192.168.4.82: worker=oc@vm02@192.168.4.82:\nhostname=ubuntu-vps-clean\nip=192.168.4.84',
        metadata={'execution_handle': 'session:ses_1', 'return_code': 0},
    )
    executor, store, task = build_executor(result)
    lane = store.get_lane('lane1')
    assert lane is not None
    store._lanes['lane1'] = replace(lane, vm_name='omniroute', ip_address='192.168.4.84')

    asyncio.run(executor.execute(task))

    final = store.get_task('task_123')
    assert final is not None
    assert final.status == 'succeeded'
    assert final.summary.startswith('oc@omniroute@192.168.4.84:')
    assert 'oc@vm02@192.168.4.82: worker=' not in final.summary
    assert final.metadata['worker_prefix'] == 'oc@omniroute@192.168.4.84:'
