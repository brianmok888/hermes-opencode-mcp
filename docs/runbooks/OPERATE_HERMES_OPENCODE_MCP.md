# Operate hermes-opencode-mcp

This runbook covers normal day-2 operations for a running `hermes-opencode-mcp` deployment.

## Operational rules

- Hermes owns topic routing; MCP owns execution.
- Use explicit `target_id` values.
- Do not claim success without a real terminal success response.
- Treat serve URL/auth fields as metadata unless a separate serve-based executor has been implemented.
- Keep troubleshooting output sanitized.

## Normal operations flow

### 1. Check service status

If using systemd:

```bash
systemctl status hermes-opencode-mcp
```

### 2. Check health

Verify the service can answer `health` and report loaded targets/state.

### 3. Check targets

Confirm the intended target exists and is ready.

### 4. Run or submit work

Use explicit target selection. Prefer a small safe validation task before important work if the environment is fresh or recently changed.

### 5. Observe execution

If using async flows:
- submit
- poll
- confirm terminal state

### 6. Review result

Confirm:
- final status
- summary/output shape
- artifacts if any
- any failure reason is explicit

## Troubleshooting order

1. service/systemd status
2. env file presence and correctness
3. targets file presence and correctness
4. target readiness
5. OpenCode CLI availability
6. MCP health
7. task state/details
8. sanitized logs

## Safe operator habits

- keep a known-good test target/task for validation
- re-check target readiness after config changes
- if systemd is used, verify restart behavior after updates
- keep repo docs and exported skills aligned with operational reality
- run skill drift checks when exported instructions change

## Related helper commands

```bash
scripts/check_hermes_skill_sync.sh operate-hermes-opencode-mcp
scripts/check_hermes_skill_sync.sh bootstrap-hermes-opencode-mcp-on-control-vm
scripts/check_hermes_skill_sync.sh prepare-opencode-target-vm
```
