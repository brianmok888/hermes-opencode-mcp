from __future__ import annotations

import json

import pytest

from hermes_opencode_mcp.config import ConfigError, load_config


def test_load_config(monkeypatch, tmp_path):
    lanes = tmp_path / 'lanes.json'
    lanes.write_text(json.dumps([{
        'lane_id': 'coding-node-1',
        'node_id': 'node-1',
        'hostname': 'vm02',
        'vm_name': 'vm02',
        'ip_address': '192.168.4.82',
        'role': 'coding-node',
        'repo_path': '/tmp/repo',
        'opencode_ready': True,
    }]))
    monkeypatch.setenv('HERMES_MCP_LANES_FILE', str(lanes))
    monkeypatch.setenv('HERMES_MCP_EXECUTOR', 'mock')
    monkeypatch.setenv('HERMES_MCP_OPENCODE_BIN', 'opencode')
    config = load_config()
    assert config.executor_mode == 'mock'
    assert 'coding-node-1' in config.lane_profiles


def test_missing_env(monkeypatch):
    monkeypatch.delenv('HERMES_MCP_LANES_FILE', raising=False)
    monkeypatch.delenv('HERMES_MCP_EXECUTOR', raising=False)
    monkeypatch.delenv('HERMES_MCP_OPENCODE_BIN', raising=False)
    with pytest.raises(ConfigError):
        load_config()
