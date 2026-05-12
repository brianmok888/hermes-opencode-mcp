from __future__ import annotations

import json

import pytest

from hermes_opencode_bridge.config import ConfigError, load_config


def _set_base_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    lanes_path = tmp_path / 'lanes.json'
    lanes_path.write_text(json.dumps([
        {
            'lane_id': 'lane1',
            'node_id': 'node1',
            'hostname': 'node1.local',
            'vm_name': 'vm02',
            'ip_address': '192.168.4.82',
            'role': 'coding-node',
            'repo_path': '/tmp/repo',
            'opencode_ready': True,
        }
    ]), encoding='utf-8')
    monkeypatch.setenv('HERMES_BRIDGE_PORT', '18097')
    monkeypatch.setenv('HERMES_BRIDGE_TOKEN', 'secret-token')
    monkeypatch.setenv('HERMES_BRIDGE_LANES_FILE', str(lanes_path))
    monkeypatch.setenv('HERMES_BRIDGE_EXECUTOR', 'mock')
    monkeypatch.setenv('HERMES_BRIDGE_OPENCODE_BIN', 'opencode')


def test_load_config_accepts_plain_ip_host(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_base_env(monkeypatch, tmp_path)
    monkeypatch.setenv('HERMES_BRIDGE_HOST', '192.168.4.82')

    config = load_config()

    assert config.host == '192.168.4.82'



def test_load_config_accepts_url_style_host(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_base_env(monkeypatch, tmp_path)
    monkeypatch.setenv('HERMES_BRIDGE_HOST', 'http://192.168.4.84:18097')

    config = load_config()

    assert config.host == '192.168.4.84'



def test_load_config_rejects_invalid_host_url(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_base_env(monkeypatch, tmp_path)
    monkeypatch.setenv('HERMES_BRIDGE_HOST', 'http://:18097')

    with pytest.raises(ConfigError):
        load_config()
