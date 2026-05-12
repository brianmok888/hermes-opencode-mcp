# Bridge capability adoption without runtime revival

Use this pattern when a bridge-to-MCP migration is already complete enough that the canonical repo should stay MCP-native, but the session surfaces still-useful operational knowledge from the old bridge era.

## Principle

Do not force a false binary between:
- reviving the old bridge runtime inside the MCP repo, and
- discarding bridge-era knowledge entirely.

Instead, absorb durable operational facts into the MCP repo in **descriptive** forms first:
- schema fields
- example config
- operator docs
- install/runbook notes
- tests that prove the metadata survives load/list/get flows

## Good candidates for descriptive adoption

- target metadata for direct `opencode serve` endpoints
- per-target auth-env naming conventions
- LAN-first operator notes
- human attach/debug handoff notes
- explicit statement that current runtime still uses CLI execution

## Example from this session

Added to `ExecutionTarget` and related examples/docs/tests:
- `opencode_base_url`
- `opencode_auth_token_env`

This preserved bridge-era knowledge about direct OpenCode serve endpoints and auth naming without reintroducing the legacy bridge runtime.

## Why this is useful

It prevents losing operational knowledge during cleanup/cutover while avoiding architecture backsliding.

## Non-goals

This pattern does **not** mean:
- automatically adding a new executor mode
- switching MCP execution from CLI to HTTP
- rebuilding the old bridge transport

Those are separate design decisions and should be implemented only when explicitly requested.
