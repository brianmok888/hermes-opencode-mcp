---
name: bootstrap-hermes-opencode-mcp-on-control-vm
version: 1.0.0
description: Bootstrap hermes-opencode-mcp on the Hermes/control-plane VM with secure config, service install, and validation.
triggers:
  - bootstrap hermes mcp
  - install hermes-opencode-mcp on control vm
  - setup control plane mcp
  - deploy hermes opencode mcp
---

# Bootstrap hermes-opencode-mcp on control VM

Use this skill when setting up the MCP service on the Hermes/control-plane VM.

## Goals

1. Install the MCP service reproducibly on the control VM.
2. Create env/config files without storing raw secrets in repo-tracked files.
3. Configure targets with explicit declared IP/address values.
4. Validate the service before handing it to operators or Hermes.

## Core rules

- The MCP service runtime remains CLI-backed via OpenCode CLI.
- Do not silently replace task execution with raw SSH or a different runtime.
- `ip_address` must be declared in target config; do not add auto-detect logic.
- If target metadata includes `opencode_base_url` or `opencode_auth_token_env`, treat them as metadata unless a separate executor mode is explicitly implemented.
- Raw auth tokens stay on the VM/service side only; repo config stores only env-var names.

## Operator questionnaire

Collect before writing config:

- Is the target VM `local network` or `remote`?
- What IP/address should be written into target config?
- Optional direct OpenCode serve URL: `http://<ip-or-hostname>:4096`
- Optional auth env var name: `<TOKEN_ENV_NAME>`

If auth is needed for `opencode serve` metadata/handoff:
- confirm the target VM already has the auth-bearing env/service config that `opencode serve` reads
- if needed, let the operator generate the token on the VM, for example:

```bash
ssh <vm-host> 'openssl rand -hex 32'
```

- store the token only on the VM side
- record only the env var name in MCP metadata/docs

## Control-VM workflow

1. Clone the repo.
2. Create a Python environment and install the package.
3. Prepare the MCP env file.
4. Prepare `targets.json` with explicit `ip_address` values.
5. Install the systemd unit if long-running service mode is wanted.
6. Start the service.
7. Validate `health`, `list_targets`, and a safe execution path.

## Validation

Prefer this order:

1. config file sanity
2. `python3 -m compileall src tests scripts`
3. manual service start
4. `health`
5. `list_targets`
6. safe mock or real task run, depending on environment
7. service restart validation if systemd is installed

## Security checklist

- no raw token values in `targets.json`
- env files are local/runtime-side, not committed
- repo docs use placeholders only
- service logs avoid full prompt/output capture by default
- any operator-facing examples stay sanitized

## Related repo docs

- `INSTALL_AND_RELEASE.md`
- `README.md`
- `deploy/systemd/hermes-opencode-mcp.service`
- `deploy/env/hermes-opencode-mcp.env.example`
- `docs/runbooks/BOOTSTRAP_HERMES_MCP_ON_CONTROL_VM.md`
