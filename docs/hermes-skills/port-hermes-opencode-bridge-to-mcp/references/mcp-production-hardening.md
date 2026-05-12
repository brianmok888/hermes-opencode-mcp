# MCP production hardening after bridge-to-MCP port

Use this reference after the MCP-native port already works and the remaining ask is "make it operationally real".

## Bundle the work together

The productive sequence from this session was:

1. add systemd/env-file deployment assets
2. add structured JSON logging with metadata-only task lifecycle events
3. add startup reconciliation for persisted `queued`/`running` tasks
4. add a live E2E script that goes through the real client/server contract
5. run unit tests separately from live-environment verification

Treat these as one hardening pass, not five unrelated chores.

## Logging pattern

Prefer a tiny local logging utility instead of pulling in a heavy dependency.

Recommended fields:
- timestamp
- level
- logger name
- message/event name
- `event` object with metadata only

Safe event payload examples:
- `task_id`
- `target_id`
- `directory`
- `text_length`
- `status`
- `dispatch_status`
- `execution_handle`
- `process_id`
- `timeout_ms`
- `startup_recovered_tasks`

Avoid by default:
- full prompt text
- full execution summary/output
- raw secrets/tokens
- copied request payload bodies

Good lifecycle events to emit:
- `task_created`
- `task_dispatch_requested`
- `task_running`
- `task_cancel_requested`
- `task_cancelled_before_dispatch`
- `task_terminal`
- `startup_reconciliation_completed`
- `rpc_request`
- `rpc_service_error`
- `rpc_unhandled_error`
- `opencode_process_started`
- `opencode_process_cancelled`
- `opencode_process_timed_out`
- `opencode_process_finished`

## Startup reconciliation pattern

If persisted state can survive process restarts, then restart recovery is part of the contract.

Recommended behavior:
- scan persisted tasks on startup
- any `queued` or `running` task becomes terminal `failed`
- set `dispatch_status=interrupted_on_startup`
- stamp a recovery timestamp such as `recovered_on_startup_at`
- degrade affected targets or at least clear stale `busy` state
- expose the count in `health`

Do not leave old in-flight tasks stuck forever. Operators need a truthful terminal state.

## Operational packaging pattern

Include deployment assets in-repo:

- `deploy/systemd/<service>.service`
- `deploy/env/<service>.env.example`

The unit should usually include:
- `WorkingDirectory=`
- `EnvironmentFile=`
- restart policy
- journald/stdout-stderr routing
- filesystem protections
- explicit writable state directory

## Live E2E pattern

A useful live script should:
- build env explicitly
- start the MCP server through the same entrypoint the user will actually run
- call the client helper, not private internals
- submit a real task with `submit_and_wait` or equivalent
- emit a JSON report with `health` + terminal task data

This is the clean separation:
- unit tests verify structure and edge cases
- live E2E verifies the real target wiring

## Verification language

When live target access was not actually exercised, say so clearly:
- implementation complete
- unit tests passed
- real target E2E script exists
- live target execution still pending environment access

Do not blur "script added" into "live environment proved".
