# hermes-opencode-mcp

MCP-native execution-target executor for OpenCode CLI workflows.

## Goal

Provide a standard MCP interface for target-based task execution while keeping the execution backend simple and portable:

```text
MCP client -> hermes-opencode-mcp -> OpenCode CLI -> result/artifacts
```

This repo intentionally uses the **OpenCode CLI** as the backend executor, not a local OpenCode runtime API.

## Routing boundary

Telegram forum-topic routing belongs in **Hermes**, not in this MCP server.

- Hermes should map `chat_id` + `topic_id` to an execution `target_id`
- Hermes should decide whether a topic message is normal chat or task submission
- `hermes-opencode-mcp` should only receive explicit execution requests for a chosen `target_id`

See [`TOPIC_ROUTING.md`](./TOPIC_ROUTING.md) for the recommended boundary, examples, and operator guidance.

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

Important: do **not** encode Telegram topic IDs into target definitions or target names. Keep targets platform-agnostic and let Hermes own topic-to-target mapping.

## Example Hermes topic routing config

See these repo-local Hermes-side routing examples:

- [`templates/topic-routing.example.yaml`](./templates/topic-routing.example.yaml)
- [`templates/topic-routing.example.json`](./templates/topic-routing.example.json)

This config is intentionally **Hermes-owned**, not MCP server config.

For a quick visual overview, see [`docs/TOPIC_ROUTING_FLOW.md`](./docs/TOPIC_ROUTING_FLOW.md).

## Exported Hermes skill copy

This repo also includes a sanitized export copy of the Hermes skill:

- [`docs/hermes-skills/hermes-telegram-topic-routing/SKILL.md`](./docs/hermes-skills/hermes-telegram-topic-routing/SKILL.md)

If you want an agent to install or recreate that skill in Hermes, use:

- [`docs/hermes-skills/INSTALL_HERMES_SKILL.md`](./docs/hermes-skills/INSTALL_HERMES_SKILL.md)

That install note includes a reusable prompt that points directly at the exported skill doc.

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

## Migration and cleanup

This repository is now the canonical home for the Hermes/OpenCode execution implementation.

Legacy bridge-specific operational assets preserved here:

- [`docs/MIGRATION_FROM_BRIDGE.md`](./docs/MIGRATION_FROM_BRIDGE.md)
- [`docs/legacy-bridge/ONBOARDING.md`](./docs/legacy-bridge/ONBOARDING.md)
- [`docs/legacy-bridge/WORKER_POLICY.md`](./docs/legacy-bridge/WORKER_POLICY.md)
- [`docs/legacy-bridge/SKILL.md`](./docs/legacy-bridge/SKILL.md)
- [`scripts/provision-bridge-target.py`](./scripts/provision-bridge-target.py)

The provisioning helper is retained only for migration / decommissioning support of old bridge deployments. The supported runtime architecture of this repository remains MCP-native.

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

## Hermes -> MCP task payload example

Once Hermes has already mapped a Telegram topic to a target, the MCP-facing request should be explicit and platform-agnostic.

Example logical payload:

```json
{
  "target_id": "coding-node-1",
  "directory": "/path/to/coding-repo",
  "text": "fix the failing import and run tests"
}
```

Equivalent Python client call:

```python
result = client.submit_and_wait(
    target_id="coding-node-1",
    directory="/path/to/coding-repo",
    text="fix the failing import and run tests",
)
```

The important design rule is that `chat_id` and `topic_id` should already have been resolved by Hermes before this call is made.

## Operational notes

- State is persisted under `HERMES_MCP_STATE_DIR` in JSON files.
- On startup, any persisted `queued` or `running` task is reconciled to a failed terminal state with `dispatch_status=interrupted_on_startup` because the prior OpenCode process cannot be resumed safely.
- Only one queued/running task is allowed per target at a time.
- `health` now reports `state_dir`, target count, current running task count, and `startup_recovered_tasks`.
- `mock` executor is for local verification only; production use should set `HERMES_MCP_EXECUTOR=opencode`.
- Logs are structured JSON by default and intentionally avoid storing full task prompts or full execution output; only metadata such as task IDs, target IDs, lengths, and execution handles are emitted.
- If Hermes is the caller, keep platform-specific routing concerns outside this repo; topic/thread mapping should be handled before invoking MCP tools.

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
