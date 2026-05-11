# hermes-opencode-mcp

MCP-native execution-target executor for OpenCode CLI workflows.

## Goal

Provide a standard MCP interface for target-based task execution while keeping the execution backend simple and portable:

```text
MCP client -> hermes-opencode-mcp -> OpenCode CLI -> result/artifacts
```

This repo intentionally uses the **OpenCode CLI** as the backend executor, not a local OpenCode runtime API.

## Production-oriented capabilities

- persistent task and target state on disk
- single-target concurrency guard (`target busy` rejection)
- synchronous and async execution flows
- execution identity prefix enforcement: `oc@vm_name@ip_address:`
- OpenCode CLI adapter with cancellation, timeout, and execution handles
- structured JSON logging with retention-safe metadata-only task events
- startup reconciliation for interrupted queued/running tasks after restart
- stdio MCP server plus Python client helper

## Current MCP tools

- `health`
- `list_targets`
- `get_target`
- `create_task`
- `submit_task`
- `get_task`
- `cancel_task`
- `get_artifacts`
- `run_task`

## Required environment variables

- `HERMES_MCP_TARGETS_FILE`
- `HERMES_MCP_EXECUTOR` (`mock` or `opencode`)
- `HERMES_MCP_OPENCODE_BIN`
- `HERMES_MCP_REPO_ROOT`
- `HERMES_MCP_STATE_DIR`

Optional:

- `HERMES_MCP_SERVER_NAME` (default: `hermes-opencode-mcp`)
- `HERMES_MCP_SERVER_VERSION` (default: `0.1.0`)
- `HERMES_MCP_LOG_LEVEL` (default: `INFO`)
- `HERMES_MCP_LOG_JSON` (`1` by default; set `0` for plain text logs)

## Example execution target file

See [`templates/targets.example.json`](./templates/targets.example.json).

## Running

```bash
export PYTHONPATH=/path/to/hermes-opencode-mcp/src
export HERMES_MCP_TARGETS_FILE=/path/to/targets.json
export HERMES_MCP_EXECUTOR=opencode
export HERMES_MCP_OPENCODE_BIN=opencode
export HERMES_MCP_REPO_ROOT=/path/to/hermes-opencode-mcp
export HERMES_MCP_STATE_DIR=/var/lib/hermes-opencode-mcp
python -m hermes_opencode_mcp
```

Or via the console script:

```bash
hermes-opencode-mcp
```

## Systemd packaging

Example deployment assets are included:

- systemd unit: [`deploy/systemd/hermes-opencode-mcp.service`](./deploy/systemd/hermes-opencode-mcp.service)
- environment file template: [`deploy/env/hermes-opencode-mcp.env.example`](./deploy/env/hermes-opencode-mcp.env.example)

Typical install flow:

```bash
sudo install -d /etc/hermes-opencode-mcp /var/lib/hermes-opencode-mcp /opt/hermes-opencode-mcp
sudo cp deploy/env/hermes-opencode-mcp.env.example /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
sudo cp deploy/systemd/hermes-opencode-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-opencode-mcp
sudo journalctl -u hermes-opencode-mcp -f
```

The systemd unit is configured for:

- `EnvironmentFile=`-driven configuration
- automatic restart on failure
- journald output for JSON log shipping/retention
- strict filesystem protections with write access limited to `HERMES_MCP_STATE_DIR`

## Python client example

```python
from hermes_opencode_mcp.client import MCPClient, MCPClientConfig

with MCPClient(
    MCPClientConfig(
        command="python3",
        args=["-m", "hermes_opencode_mcp"],
        env={
            "PYTHONPATH": "/path/to/hermes-opencode-mcp/src",
            "HERMES_MCP_TARGETS_FILE": "/path/to/targets.json",
            "HERMES_MCP_EXECUTOR": "opencode",
            "HERMES_MCP_OPENCODE_BIN": "opencode",
            "HERMES_MCP_REPO_ROOT": "/path/to/hermes-opencode-mcp",
            "HERMES_MCP_STATE_DIR": "/var/lib/hermes-opencode-mcp",
        },
        cwd="/path/to/hermes-opencode-mcp",
    )
) as client:
    print(client.health())
    print(client.list_targets())
    result = client.submit_and_wait(
        target_id="coding-node-1",
        text="Fix the failing test",
        directory="/repo/path",
    )
    print(result)
```

## Operational notes

- State is persisted under `HERMES_MCP_STATE_DIR` in JSON files.
- On startup, any persisted `queued` or `running` task is reconciled to a failed terminal state with `dispatch_status=interrupted_on_startup` because the prior OpenCode process cannot be resumed safely.
- Only one queued/running task is allowed per target at a time.
- `health` now reports `state_dir`, target count, current running task count, and `startup_recovered_tasks`.
- `mock` executor is for local verification only; production use should set `HERMES_MCP_EXECUTOR=opencode`.
- Logs are structured JSON by default and intentionally avoid storing full task prompts or full execution output; only metadata such as task IDs, target IDs, lengths, and execution handles are emitted.

## Live E2E verification

Use the included live verification script against a real OpenCode-ready target:

```bash
python scripts/e2e_live.py \
  --target-id coding-node-1 \
  --directory /path/to/repo \
  --targets-file /etc/hermes-opencode-mcp/targets.json
```

The script starts the MCP server locally, submits a real `submit_and_wait` task through the client, and verifies the terminal task contract, including execution prefix and execution handle requirements.

## CI

A GitHub Actions workflow is included at [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).

It runs:

- `unit-tests`: always runs `pytest -q` using the mock executor path
- `live-e2e`: runs only when explicit repo/org configuration is present

### Conditional live E2E configuration

Set these GitHub Actions **Variables**:

- `HERMES_MCP_E2E_ENABLED=1`
- `HERMES_MCP_E2E_TARGET_ID=<target_id>`
- `HERMES_MCP_E2E_DIRECTORY=<repo_path_on_target>`
- `HERMES_MCP_OPENCODE_BIN=opencode` (optional if `opencode` is already on `PATH`)
- `HERMES_MCP_E2E_TEXT=<verification prompt>` (optional)

Set this GitHub Actions **Secret**:

- `HERMES_MCP_TARGETS_JSON_B64`: base64-encoded contents of the targets JSON file

Example secret preparation:

```bash
base64 -w0 /path/to/targets.json
```

Once those are present, the workflow automatically:

1. installs the package in editable mode with test deps
2. runs mock tests
3. decodes the targets config into a temporary file
4. invokes `scripts/e2e_live.py` against the configured real target

If the variables/secrets are absent, the live E2E job is skipped cleanly and CI still validates the mock path.
