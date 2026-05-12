# Legacy track removal after an MCP port

Use this after the MCP-native implementation is already complete and the user wants the repo cleaned so only active MCP code remains.

## Why this matters

A successful port often leaves behind a second phase of work:
- archived bridge source trees
- migration-only docs
- helper scripts kept temporarily for cutover
- old template files preserving lane/bridge terminology

If the user later says to "remove the legacy tracks", do not treat that as a pure delete task. First confirm the active MCP code already absorbed the useful behavior.

## Recommended sequence

1. Compare legacy archive vs active MCP package.
   - Read the legacy README, config, executor, client/routing helpers, and tests.
   - Read the active MCP service, models, config, client, adapter, tests, and docs.
   - Identify whether anything in the archive still represents live runtime behavior or operator-critical workflow.

2. Distinguish runtime features from historical artifacts.
   - Keep MCP runtime features in `src/`, tests, templates, and current docs.
   - Remove bridge-only HTTP server code, migration notes, decommission helpers, and archive copies once they are no longer needed.

3. Run a residual-search pass before deleting.
   Search tracked repo content for markers such as:
   - archived package name (`hermes-opencode-bridge`)
   - old env var prefixes (`HERMES_BRIDGE_`)
   - migration docs (`MIGRATION_FROM_BRIDGE`)
   - migration-only helper names (`provision-bridge-target.py`)
   - old concept names that should no longer be public

   Exclude noise directories like `.git/`, `.venv/`, and `__pycache__/`.

4. Review tracked paths explicitly.
   - Use `git ls-files` to understand the tracked legacy surface.
   - Use `git status --short` before and after cleanup so deletions are intentional.

5. Update docs after deletion.
   - README should no longer say legacy bridge assets are preserved if they were removed.
   - install/release docs should stop instructing operators to preserve migration-era assets once cutover is finished.

6. Validate and ship.
   - Run tests (`pytest -q` or equivalent).
   - Commit with a cleanup-specific message.
   - Push only after docs and tracked-file review are consistent with the deletion.

## Concrete example from this session

The cleanup removed:
- `legacy/hermes-opencode-bridge/`
- `docs/legacy-bridge/`
- `docs/MIGRATION_FROM_BRIDGE.md`
- `scripts/provision-bridge-target.py`
- `templates/lanes.example.json`

And then updated:
- `README.md`
- `INSTALL_AND_RELEASE.md`

Validation after cleanup:
- `pytest -q` passed
- commit created and pushed successfully

## Pitfall

Do not leave README/install docs claiming the repo preserves legacy tracks after you just deleted those tracks. Cleanup is not complete until the documentation matches the new canonical state.
