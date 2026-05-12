from __future__ import annotations

import json

import pytest

from hermes_opencode_mcp.config import ConfigError, load_config


def test_load_config(monkeypatch, tmp_path):
    targets = tmp_path / 'targets.json'
    state_dir = tmp_path / 'state'
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    targets.write_text(json.dumps([{
        'target_id': 'coding-node-1',
        'node_id': 'node-1',
        'hostname': 'vm02',
        'vm_name': 'vm02',
        'ip_address': '192.168.4.82',
        'role': 'coding-node',
        'repo_path': '/tmp/repo',
        'opencode_ready': True,
        'opencode_base_url': 'http://192.168.4.82:4096',
        'opencode_auth_token_env': 'VM02_OPENCODE_TOKEN',
    }]))
    monkeypatch.setenv('HERMES_MCP_TARGETS_FILE', str(targets))
    monkeypatch.setenv('HERMES_MCP_EXECUTOR', 'mock')
    monkeypatch.setenv('HERMES_MCP_OPENCODE_BIN', 'opencode')
    monkeypatch.setenv('HERMES_MCP_REPO_ROOT', str(repo_root))
    monkeypatch.setenv('HERMES_MCP_STATE_DIR', str(state_dir))
    config = load_config()
    assert config.executor_mode == 'mock'
    assert 'coding-node-1' in config.execution_targets
    assert config.state_dir == state_dir
    assert config.log_level == 'INFO'
    assert config.log_json is True
    assert config.execution_targets['coding-node-1'].opencode_base_url == 'http://192.168.4.82:4096'
    assert config.execution_targets['coding-node-1'].opencode_auth_token_env == 'VM02_OPENCODE_TOKEN'


def test_missing_env(monkeypatch):
    monkeypatch.delenv('HERMES_MCP_TARGETS_FILE', raising=False)
    monkeypatch.delenv('HERMES_MCP_EXECUTOR', raising=False)
    monkeypatch.delenv('HERMES_MCP_OPENCODE_BIN', raising=False)
    monkeypatch.delenv('HERMES_MCP_REPO_ROOT', raising=False)
    monkeypatch.delenv('HERMES_MCP_STATE_DIR', raising=False)
    with pytest.raises(ConfigError):
        load_config()


def test_invalid_log_level(monkeypatch, tmp_path):
    targets = tmp_path / 'targets.json'
    state_dir = tmp_path / 'state'
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    targets.write_text(json.dumps([{
        'target_id': 'coding-node-1',
        'node_id': 'node-1',
        'hostname': 'vm02',
        'vm_name': 'vm02',
        'ip_address': '192.168.4.82',
        'role': 'coding-node',
        'repo_path': '/tmp/repo',
        'opencode_ready': True,
    }]))
    monkeypatch.setenv('HERMES_MCP_TARGETS_FILE', str(targets))
    monkeypatch.setenv('HERMES_MCP_EXECUTOR', 'mock')
    monkeypatch.setenv('HERMES_MCP_OPENCODE_BIN', 'opencode')
    monkeypatch.setenv('HERMES_MCP_REPO_ROOT', str(repo_root))
    monkeypatch.setenv('HERMES_MCP_STATE_DIR', str(state_dir))
    monkeypatch.setenv('HERMES_MCP_LOG_LEVEL', 'VERBOSE')
    with pytest.raises(ConfigError, match='HERMES_MCP_LOG_LEVEL'):
        load_config()
