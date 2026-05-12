import asyncio

from hermes_opencode_bridge.executor import TaskExecutor
from hermes_opencode_bridge.opencode_adapter import OpenCodeAdapter, parse_opencode_output


def test_parse_opencode_output_collects_text_and_session() -> None:
    output = """noise
{"type":"text","sessionID":"ses_123","part":{"text":"hello"}}
{"type":"text","sessionID":"ses_123","part":{"text":"world"}}
"""
    summary, session_id = parse_opencode_output(output)
    assert summary == "hello\n\nworld"
    assert session_id == "ses_123"


def test_parse_opencode_output_sanitizes() -> None:
    output = '{"type":"text","sessionID":"ses_1","part":{"text":"Authorization: Bearer abc123"}}'
    summary, _ = parse_opencode_output(output)
    assert "abc123" not in summary


def test_prefix_summary_applies_worker_identity() -> None:
    prefixed = TaskExecutor._prefix_summary('oc@vm02@192.168.4.82:', 'hello')
    assert prefixed == 'oc@vm02@192.168.4.82: hello'


def test_prefix_summary_is_idempotent() -> None:
    prefixed = TaskExecutor._prefix_summary('oc@vm02@192.168.4.82:', 'oc@vm02@192.168.4.82: hello')
    assert prefixed == 'oc@vm02@192.168.4.82: hello'


def test_merge_metadata_overlays_in_order() -> None:
    merged = TaskExecutor._merge_metadata({'a': 1, 'b': 2}, {'b': 3}, {'c': 4})
    assert merged == {'a': 1, 'b': 3, 'c': 4}


def test_build_result_metadata_prefers_session_handle() -> None:
    metadata = OpenCodeAdapter._build_result_metadata(
        {'process_id': 42, 'command': ['opencode']},
        0,
        '{"type":"text","sessionID":"ses_123","part":{"text":"done"}}',
    )
    assert metadata['return_code'] == 0
    assert metadata['session_id'] == 'ses_123'
    assert metadata['execution_handle'] == 'session:ses_123'
    assert metadata['parsed_summary_present'] is True


def test_build_result_metadata_falls_back_to_pid_handle() -> None:
    metadata = OpenCodeAdapter._build_result_metadata(
        {'process_id': 77, 'command': ['opencode']},
        1,
        'plain stderr without json',
    )
    assert metadata['return_code'] == 1
    assert metadata['execution_handle'] == 'pid:77'
    assert 'session_id' not in metadata
    assert 'parsed_summary_present' not in metadata


def test_run_can_cancel_during_execution(monkeypatch) -> None:
    class FakeProc:
        def __init__(self) -> None:
            self.pid = 99
            self.returncode = None
            self.killed = False

        async def wait(self) -> int:
            await asyncio.sleep(60)
            return 0

        def kill(self) -> None:
            self.killed = True
            self.returncode = -9

        async def communicate(self):
            return (b'', b'')

    fake_proc = FakeProc()

    async def fake_create_subprocess_exec(*args, **kwargs):
        return fake_proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create_subprocess_exec)
    adapter = OpenCodeAdapter('python')

    result = asyncio.run(
        adapter.run(
            text='pwd',
            directory='/tmp',
            timeout_ms=5000,
            cancel_check=lambda: True,
        )
    )

    assert result.cancelled is True
    assert result.error == 'opencode execution cancelled during execution'
    assert result.metadata['execution_handle'] == 'pid:99'
    assert result.metadata['cancelled'] is True
    assert fake_proc.killed is True
