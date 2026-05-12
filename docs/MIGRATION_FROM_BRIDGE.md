# Migration from hermes-opencode-bridge

This repository is the canonical home for the Hermes/OpenCode execution stack.

The older `hermes-opencode-bridge` repository should be treated as deprecated and scheduled for removal after all useful operational assets are preserved here.

## What was migrated here

- the active OpenCode execution implementation lives in this MCP repository
- legacy bridge onboarding notes were copied into `docs/legacy-bridge/`
- the legacy bridge provisioning helper was copied into `scripts/provision-bridge-target.py`
- bridge-specific worker policy text was preserved for audit/reference

## Cleanup intent

After this migration:

1. stop making functional changes in `hermes-opencode-bridge`
2. keep this repo as the single source of truth
3. delete the old bridge repo checkout once this repo is pushed and verified
4. delete the remote bridge repo separately if desired and if GitHub permissions allow it

## Important boundary

The preserved bridge helper/script is retained for operational cleanup and migration support.
It does **not** redefine this repository's architecture boundary: the supported runtime architecture remains MCP-native and CLI-first.
