# Hermes-opencode-bridge

Generic bridge architecture for Hermes to delegate work to onboarded OpenCode target nodes.

## Goal

Provide a bootstrap-first, security-first execution model where:

```
User -> Hermes -> target node worker/bridge -> OpenCode -> result/artifacts -> Hermes
```

Hermes remains the control plane. Target nodes provide execution capability after onboarding.

## Design principles

- generic, public-friendly architecture
- bootstrap target nodes before normal operation
- security audit and sanitization are mandatory
- strict `.gitignore` hygiene
- fail-fast configuration
- role-based routing: coding node vs runtime node
- no hardwired dependency on private VM names

## Roles

### Coding node
A target node allowed to edit code, commit, and push.

### Runtime node
A target node allowed to pull, run, test, and validate runtime behavior.

### Hermes
The control plane that receives requests, selects the target node, applies policy, and returns sanitized results.

## Bootstrap-first workflow

1. discover target node environment
2. install or validate OpenCode
3. establish worker/bridge execution path
4. verify repo/git/runtime readiness
5. apply security baseline
6. register node profile for Hermes routing

## Current implementation direction

Initial delivery loop:

1. code on an onboarded coding node
2. push to GitHub
3. pull on an onboarded runtime node
4. run and test locally

## Documentation

- [ONBOARDING.md](./ONBOARDING.md) — generic onboarding and bootstrap process
- [SKILL.md](./SKILL.md) — reusable Hermes skill/playbook
- `scripts/provision-bridge-target.py` — bootstrap helper to sync bridge tokens, render the user service, and manage bind-host selection (`--bind-host <ip>` or `--bind-host auto`)

### Provisioning helper notes

- `--bind-host auto` forces fresh auto-detection even when a target has a configured fallback address.
- `--detect-only` prints the configured bind host, current service bind host, detected bind host, and whether the service would change.
- normal runs print the same bind-host summary plus whether the bind host changed during reprovisioning.

## License

MIT


## Phase 1 MVP

This repository now includes a Python MVP skeleton for a worker bridge with:

- bearer-token auth
- configurable host binding
- lane profile loading
- task submission and polling endpoints
- in-memory task store
- output sanitization primitives

Run locally after creating a lane profile JSON file and exporting required environment variables.


## Hermes integration MVP

This repo now includes a minimal Hermes-facing integration layer:

- `hermes_client.py` — submit/poll bridge tasks from Hermes or any control-plane helper
- `routing.py` — load topic-to-lane mappings from a JSON route table
- `templates/topic_routes.example.json` — example private deployment overlay for Telegram topic routing

Recommended routing split for private deployments:

- generic Hermes topic remains separate from OpenCode workflow topics
- each dedicated machine/topic lane is bound to exactly one OpenCode worker context
- work inside a dedicated lane must go through that lane's OpenCode worker, not raw shell fallback and not another lane's worker
- coding-node topics route to coding-node bridge lanes
- runtime/OpenCode topics route to runtime-node bridge lanes

### Hard routing rules

- `generic_topic_id` is the Hermes orchestration/chat lane only; it is not a machine worker lane
- every dedicated topic must be declared explicitly in `routes`
- a dedicated topic may execute work only through its mapped OpenCode worker lane
- OpenCode-aware checks must use the OpenCode runtime/API first, not plain shell-first interpretation
- short runtime queries such as `pwd`, `whoami`, `hostname`, or `what agent oc now?` in a dedicated lane should be treated as worker introspection requests
- if a request arrives in the generic Hermes topic and needs machine/runtime introspection, Hermes should redirect to the correct dedicated lane or ask the user to pick one
- every OpenCode worker response must be prefixed exactly in worker identity form: `oc@vm_name@ip_address:`

### Lane profile requirements

Each dedicated worker lane profile must include:

- `vm_name`
- `ip_address`

These fields are used to enforce the worker response prefix contract: `oc@vm_name@ip_address:`.

Keep tokens in environment variables referenced by `secret_env`; never commit secrets into route files.
