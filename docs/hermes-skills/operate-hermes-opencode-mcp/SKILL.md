---
name: operate-hermes-opencode-mcp
version: 1.0.0
description: Normal day-2 operations for hermes-opencode-mcp including health checks, target review, task execution, troubleshooting, and safe handoff.
triggers:
  - operate hermes mcp
  - normal run operation
  - day 2 mcp ops
  - health check hermes opencode mcp
---

# Operate hermes-opencode-mcp

Use this skill for normal ongoing operations after the service is already installed.

## Goals

1. Run routine health and readiness checks.
2. Verify targets before dispatching work.
3. Execute, observe, and troubleshoot tasks safely.
4. Keep operations aligned with the CLI-backed MCP architecture.

## Daily/normal operations checklist

1. Check service status.
2. Check MCP `health`.
3. Check `list_targets` and confirm the intended target is ready.
4. Run or submit the task with an explicit `target_id`.
5. Poll status if using async flows.
6. Review result summary, status, and artifacts.
7. If there is failure, inspect sanitized logs/state and report a precise blocker.

## Core rules

- Keep topic routing in Hermes and execution in MCP.
- Keep `target_id` explicit.
- Do not claim execution succeeded unless the MCP service returned a real terminal success state.
- Treat `opencode_base_url` as metadata/handoff info unless a dedicated serve executor exists.
- Prefer sanitized logs and metadata over dumping raw prompts or outputs broadly.

## Typical operator tasks

- confirm service is running
- confirm targets are loaded
- inspect whether a target is marked ready
- run a small safe validation task
- cancel a stuck task if needed
- verify restart recovery behavior after service restart
- hand off a clean operational summary to another operator or agent

## Troubleshooting order

1. service process/systemd status
2. env file and targets file presence
3. target readiness and repo path sanity
4. OpenCode CLI availability on the control/target workflow being used
5. MCP `health`
6. task record/status details
7. sanitized logs

## Security checklist

- do not expose raw secrets while troubleshooting
- do not add private deployment identifiers to exported docs/skills
- do not store raw auth values in target metadata
- preserve sanitized examples in any copied instructions

## Related repo doc

- `docs/runbooks/OPERATE_HERMES_OPENCODE_MCP.md`
