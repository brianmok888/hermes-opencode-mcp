# Bootstrap hermes-opencode-mcp on the Hermes/control VM

This runbook is for installing and validating `hermes-opencode-mcp` on the Hermes/control-plane VM.

## Security and architecture rules

- Keep runtime execution CLI-backed via OpenCode CLI.
- Do not silently replace runtime execution with raw SSH.
- `ip_address` in target config must be operator-provided/declared.
- Do not store raw tokens in repo-tracked files or `targets.json`.
- Optional `opencode_base_url` and `opencode_auth_token_env` are metadata only unless a new executor mode is explicitly added later.

## Operator questionnaire

Collect before writing config:

- VM type: `local network` or `remote`
- VM IP/address: `<ip-or-hostname>`
- optional direct OpenCode endpoint metadata: `<scheme>://<ip-or-hostname>:<port>`
- optional auth env var name metadata: `<TOKEN_ENV_NAME>`

If auth metadata is recorded:
- confirm the target VM already has the auth-bearing env/service config for that endpoint
- if needed, generate on the VM side only:

```bash
ssh <vm-host> 'openssl rand -hex 32'
```

- keep the token on the VM side only
- record only the env var name in metadata

## Bootstrap steps

### 1. Clone the repo

```bash
git clone <repo-url>
cd hermes-opencode-mcp
```

### 2. Create environment and install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

If `venv` or `pytest` is missing, document the limitation and continue with direct validation.

### 3. Prepare env file

Use the example:

```bash
cp deploy/env/hermes-opencode-mcp.env.example /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
```

Fill runtime-local values only. Do not commit them.

### 4. Prepare targets file

Use:

```bash
cp templates/targets.example.json /etc/hermes-opencode-mcp/targets.json
```

Then edit it with explicit target values. Example shape:

```json
[
  {
    "target_id": "coding-target",
    "node_id": "node-a",
    "hostname": "devbox-a",
    "vm_name": "devbox-a",
    "ip_address": "10.0.0.10",
    "role": "coding-node",
    "repo_path": "/path/to/repo/on/target",
    "opencode_ready": true,
    "opencode_base_url": "http://10.0.0.10:<port>",
    "opencode_auth_token_env": "VM02_OPENCODE_TOKEN"
  }
]
```

Only the env var name belongs here, not the raw token.

### 5. Validate Python files

```bash
python3 -m compileall src tests scripts
```

### 6. Run manual service test

```bash
python -m hermes_opencode_mcp
```

Or use your intended launch path.

### 7. Install systemd service

Review and adapt:

- `deploy/systemd/hermes-opencode-mcp.service`

Then enable/start it.

### 8. Validate operations

- `health`
- `list_targets`
- safe task execution path
- restart behavior if using systemd

## Done criteria

Bootstrap is done when:
- control VM install is complete
- env file and targets file exist locally
- config uses explicit declared target IP/address values
- service starts successfully
- basic MCP validation succeeds
