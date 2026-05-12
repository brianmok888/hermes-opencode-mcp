---
name: hermes-opencode-bridge
version: 1.0.0
description: Generic bootstrap-first playbook for Hermes routing to onboarded OpenCode target nodes with strict security and sanitization.
triggers:
  - opencode bridge
  - onboard target vm
  - coding node
  - runtime node
  - bootstrap worker
---

# Hermes-opencode-bridge

Use this skill when Hermes needs to route work to a target machine through an OpenCode-based execution path.

## Principles

1. Hermes is the control plane.
2. Target nodes are execution planes.
3. Bootstrap first; do not assume a node is ready.
4. Prefer OpenCode-managed execution after onboarding.
5. Enforce security audit, sanitization, and strict `.gitignore` hygiene.
6. Route by role and capability, not private hostnames.

## Target roles

### Coding node
Use for code edits, commits, and pushes.

### Runtime node
Use for pull, run, test, and validation tasks.

## Bootstrap checklist

1. discover environment
2. validate or install OpenCode
3. confirm repo/git/runtime readiness
4. confirm secure local state handling
5. verify bridge/worker execution path
6. save node profile for routing

## Security checklist

- check for tracked secrets
- verify `.gitignore` strictness
- avoid exposing env values or tokens
- sanitize outputs before returning results
- fail fast on missing required config

## Routing rule

- send coding tasks to an onboarded coding node
- send run/test tasks to an onboarded runtime node

## Hard lane rules

- treat Hermes as the control plane and dedicated Telegram topics as worker-bound lanes
- each dedicated lane must work only through its mapped OpenCode worker
- do not answer dedicated-lane work through generic Hermes chat interpretation
- do not use raw shell as the default path for OpenCode-aware checks
- for OpenCode-aware checks, inspect via OpenCode runtime/API first
- if a message lands in the generic Hermes topic, do not pretend it came from a worker lane; redirect or ask for the target lane
- terse inputs like `pwd`, `whoami`, `hostname`, and `what agent oc now?` inside dedicated lanes should be treated as worker/runtime introspection first
- every worker response must include the exact worker identity prefix form `oc@vm_name@ip_address:`

## Verification

A node is ready only when:

- OpenCode works
- git workflow works for its role
- security baseline passes
- Hermes can target it safely
