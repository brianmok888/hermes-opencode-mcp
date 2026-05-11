# hermes-opencode-mcp

MCP-native lane orchestrator for Hermes/OpenCode workflows.

## Goal

Provide a standard MCP interface for lane-based task execution while keeping the execution backend simple and portable:

```text
User -> Hermes -> MCP client/router -> hermes-opencode-mcp -> OpenCode CLI -> result/artifacts -> Hermes
```

This repo intentionally uses the **OpenCode CLI** as the backend executor, not a local OpenCode runtime API.

## Why CLI-first

- no daemon requirement
- easier bootstrap on new VMs
- fewer moving parts than a runtime `/api`
- consistent with lane-oriented worker execution

## Current capabilities

- load lane profiles from JSON
- expose MCP tools for:
  - `health`
  - `list_lanes`
  - `get_lane`
  - `create_task`
  - `submit_task`
  - `get_task`
  - `cancel_task`
  - `get_artifacts`
  - `run_task`
- expose MCP resources for:
  - lane profile example
  - worker policy
  - architecture overview
- expose MCP prompts for common coding/runtime tasks
- run over stdio with JSON-RPC-style messages
- include a simple Python MCP client helper for Hermes-side integration
- include topic-route config loading for Telegram topic to lane mapping outside the server

## Configuration

Required environment variables:

- `HERMES_MCP_LANES_FILE`
- `HERMES_MCP_EXECUTOR` (`mock` or `opencode`)
- `HERMES_MCP_OPENCODE_BIN`

Optional:

- `HERMES_MCP_SERVER_NAME` (default: `hermes-opencode-mcp`)
- `HERMES_MCP_SERVER_VERSION` (default: `0.1.0`)
- `HERMES_MCP_REPO_ROOT` (used for resource file resolution)

## Example lane file

See [`templates/lanes.example.json`](./templates/lanes.example.json).

## Example topic route file

See [`templates/topic_routes.example.json`](./templates/topic_routes.example.json).

## Running

```bash
export PYTHONPATH=/path/to/hermes-opencode-mcp/src
export HERMES_MCP_LANES_FILE=/path/to/lanes.json
export HERMES_MCP_EXECUTOR=mock
export HERMES_MCP_OPENCODE_BIN=opencode
python -m hermes_opencode_mcp
```

Or via the console script:

```bash
hermes-opencode-mcp
```

## Hermes-side integration sketch

```python
from hermes_opencode_mcp.client import MCPClient, MCPClientConfig

with MCPClient(
    MCPClientConfig(
        command="python3",
        args=["-m", "hermes_opencode_mcp"],
        env={
            "PYTHONPATH": "/path/to/hermes-opencode-mcp/src",
            "HERMES_MCP_LANES_FILE": "/path/to/lanes.json",
            "HERMES_MCP_EXECUTOR": "opencode",
            "HERMES_MCP_OPENCODE_BIN": "opencode",
        },
        cwd="/path/to/hermes-opencode-mcp",
    )
) as client:
    result = client.submit_and_wait(
        lane_id="coding-node-1",
        text="Fix the failing test",
        directory="/repo/path",
    )
```

## Notes

- Telegram topic ID to lane ID routing should stay in Hermes.
- This server should receive an already-resolved `lane_id` from the caller.
- Worker responses preserve the `oc@vm_name@ip_address:` identity prefix contract.
- The repo includes both synchronous execution (`run_task`) and async submit+poll (`submit_task` + `get_task`).
- Artifacts are modeled in the API so later file collection can be added without reshaping the task format.
