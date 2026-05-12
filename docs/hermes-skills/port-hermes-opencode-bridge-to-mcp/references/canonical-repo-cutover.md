# Canonical repo cutover when bridge and MCP repos coexist

Use this when both `hermes-opencode-bridge` and `hermes-opencode-mcp` exist at the same time and the user wants MCP to become canonical.

## Main risk

After a long session or context compression, it is easy to keep working in the last-touched bridge repo and accidentally commit/push there even though the real target is MCP.

## Required pre-commit check

Before commit/push, always confirm all four in the intended repo:

1. current directory / repo root
2. `git remote -v`
3. current branch
4. `git status --short`

If two similarly named repos exist side-by-side, say the intended repo name explicitly in the status summary.

## Cutover pattern

1. Identify the canonical destination repo first.
2. Compare bridge-only assets against the MCP repo.
3. Move still-useful operational assets into MCP:
   - provisioning helper scripts
   - onboarding/deployment notes
   - worker/policy docs
   - migration/decommissioning notes
4. Update MCP README/install docs to say MCP is canonical.
5. Validate in MCP (`pytest`, helper smoke check, docs sanity).
6. Commit/push MCP.
7. Only after MCP is verified, remove or archive the old bridge repo.

## Reporting rule

Report implementation migration and cleanup separately:

- "canonical repo updated and pushed"
- "legacy bridge repo ready for local deletion / remote deletion"

Do not imply the old repo is gone until it is actually removed.
