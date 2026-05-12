# Bridge provisioning helper pattern

Use this when an MCP/OpenCode bridge needs a repeatable operator command to keep Hermes env, remote target env, lane/target metadata, and systemd service state in sync.

## Why this belongs in-repo

A local-only bootstrap script is easy to lose and hard for future operators or agents to discover. If the script is part of the deployment workflow, check it into the repo under `scripts/` and mention it in `README.md`.

## Minimum behavior

1. Accept a named target (for example `vm01`, `vm02`, `omniroute`).
2. Choose token from a stable precedence order unless forced rotation is requested:
   - local Hermes env token
   - existing target env token
   - newly generated token
3. Validate the target environment before writing service files.
4. Render/update the user systemd unit and target metadata file.
5. Restart the target service.
6. Optionally restart the local Hermes gateway when the local control-plane env changed.

## Bind-host handling contract

The script should support three operational modes:

- `--bind-host <ip>` → force a specific bind address
- no `--bind-host` → normal auto-detect path
- `--bind-host auto` → explicitly force fresh auto-detection

This explicit `auto` mode matters because operators may otherwise assume a configured fallback address is what the service is currently using.

## Detect-only output contract

A `--detect-only` mode should print machine-readable `key=value` lines covering at least:

- `target`
- `configured_bind_host`
- `current_service_bind_host`
- `bind_host`
- `bind_source`
- `bind_host_would_change`

## Normal run output contract

A normal provisioning run should print enough summary to confirm the applied state without manually opening env files or unit files. Include at least:

- `target`
- `token_source`
- `env_key`
- `target_host`
- `target_service`
- `lanes_file` or equivalent target metadata file
- `configured_bind_host`
- `current_service_bind_host`
- `bind_host`
- `bind_source`
- `bind_host_changed`
- `token_synced=yes`
- optional `gateway_pid` when the local gateway is restarted

## Validation pattern

After adding the helper to the repo:

1. run `--detect-only` against a real target
2. run repo tests via the project venv or `uv run pytest -q`
3. review `git diff` for both the helper and docs
4. commit the helper and any generated lockfile intentionally, not by accident

## Pitfall

If system state is managed by a script but the script lives only in `~/.hermes/` or another local path, the repo will drift from real operations. Treat repeatable provisioning logic as productized operational code, not personal scratch state.
