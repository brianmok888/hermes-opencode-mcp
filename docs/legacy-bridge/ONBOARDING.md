# Legacy bridge onboarding guide

This document was migrated from `hermes-opencode-bridge` for reference during cleanup.

It describes how the older bridge-shaped deployment onboarded a target machine.
It is preserved because parts of the operational rollout and decommissioning still depend on those concepts.

## Objective

Turn a target machine into one of the following:

- **coding node**: edit, commit, push
- **runtime node**: pull, run, test

## Preferred bootstrap path

Use OpenCode TUI self-install / self-validation on the target whenever possible.

The target should be instructed to:

1. inspect OS, package manager, runtimes, git, curl, and repo state
2. install OpenCode if missing
3. validate OpenCode command availability and version
4. prepare or validate the worker/bridge execution path
5. apply security and `.gitignore` checks
6. return sanitized readiness results

## Temporary bootstrap fallback

If the target is not yet OpenCode-capable, a one-time bootstrap channel such as SSH may be used only to establish the normal OpenCode-managed path.

## Prerequisites

Before marking a target ready, verify:

- node identity and intended role
- OpenCode availability
- git availability
- repo path availability
- push/pull permissions as appropriate
- runtime dependencies
- secret handling plan
- strict `.gitignore` coverage
- safe log/cache/runtime-state handling

## Security gates

Required before activation:

- no secrets committed
- env files ignored
- logs/state/cache ignored or controlled
- sanitized output policy defined
- fail-fast config policy applied

## Readiness criteria

A node is onboarded only when:

- OpenCode is installed and validated
- the execution path is known and usable
- repo workflow is valid for the node role
- security checks pass
- Hermes can route by role/capability

## Role assignment

### Coding node
Must support:

- repo edits
- commit workflow
- push workflow
- secure development state handling

### Runtime node
Must support:

- pull/update workflow
- local run/test
- health verification
- sanitized result reporting

## Output expectations

Bootstrap and validation responses must avoid leaking:

- secrets
- tokens
- private env content
- unnecessary internal paths
- raw sensitive logs
