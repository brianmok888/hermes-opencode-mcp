# INSTALL_AND_RELEASE.md runbook pattern

Use this reference when a production-hardening port also needs a concrete operator/AI-agent handoff document.

## When to add the file

Add `INSTALL_AND_RELEASE.md` when the user asks for:
- simpler install instructions
- an AI-agent-friendly onboarding guide
- exact run/config steps
- explicit commit / merge / push instructions

Do not hide these steps only inside a long README if the user explicitly wants an operational runbook.

## Recommended structure

1. Purpose / what this repo does
2. Preflight checks
3. Clone repo
4. Create virtual environment and install package/dev deps
5. Create required directories
6. Create or copy targets file
7. Create env file from example
8. Manual run command
9. Verify with `pytest -q`
10. Optional live E2E script invocation
11. Optional systemd install/enable/start steps
12. Git commit / merge / push sequence
13. Final validation checklist
14. Gotchas / common mistakes

## Writing style for this user

- Keep it copy-pasteable.
- Prefer imperative steps over architecture explanation.
- Include exact paths and commands.
- Add verification checkpoints after each major step.
- If the user says to simplify, shorten the prose and make the top of the file actionable first.

## Session-specific example

In this session, the useful runbook covered:
- preflight checks
- clone + venv install
- required directories
- `targets.json` creation/validation
- env-file creation from `deploy/env/hermes-opencode-mcp.env.example`
- manual server run
- `pytest -q`
- optional `scripts/e2e_live.py`
- systemd setup with `deploy/systemd/hermes-opencode-mcp.service`
- git commit/merge/push steps

This complements README-style architecture docs and should be linked from the umbrella skill when present.
