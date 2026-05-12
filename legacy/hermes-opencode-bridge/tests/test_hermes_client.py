from hermes_opencode_bridge.hermes_client import BridgeClient, BridgeClientConfig, BridgeClientError


def build_client() -> BridgeClient:
    return BridgeClient(BridgeClientConfig(base_url='http://192.168.4.82:18097', bearer_token='secret-token'))


def test_validate_terminal_task_accepts_cancelled_during_execution() -> None:
    client = build_client()
    task = {
        'status': 'cancelled',
        'summary': 'oc@vm01@192.168.4.81: Task cancelled during execution.',
        'error': 'oc@vm01@192.168.4.81: opencode execution cancelled during execution',
        'metadata': {
            'dispatch_status': 'cancelled_during_execution',
            'execution_handle': 'pid:99',
            'worker_prefix': 'oc@vm01@192.168.4.81:',
        },
    }

    validated = client._validate_terminal_task(  # type: ignore[attr-defined]
        task,
        require_worker_prefix=True,
        require_execution_handle=True,
    )

    assert validated is task


def test_validate_terminal_task_rejects_unknown_dispatch_status() -> None:
    client = build_client()
    task = {
        'status': 'cancelled',
        'summary': 'oc@vm01@192.168.4.81: Task cancelled during execution.',
        'metadata': {
            'dispatch_status': 'cancelled_midflight',
            'execution_handle': 'pid:99',
            'worker_prefix': 'oc@vm01@192.168.4.81:',
        },
    }

    try:
        client._validate_terminal_task(  # type: ignore[attr-defined]
            task,
            require_worker_prefix=True,
            require_execution_handle=True,
        )
    except BridgeClientError as exc:
        assert 'dispatch_status' in str(exc)
    else:
        raise AssertionError('expected BridgeClientError')
