# Worker / Orchestrator hard policy

## Scope

This file defines the non-optional behavior contract between Hermes and dedicated OpenCode worker lanes.

## Hard rules

1. Hermes is the orchestrator. Dedicated machine topics are worker lanes.
2. Each dedicated lane is bound to exactly one OpenCode worker.
3. Dedicated lanes must execute through their mapped OpenCode worker only.
4. Do not use raw shell as the default path for OpenCode worker tasks.
5. CLI-based `opencode run ...` is the supported execution backend for this repo.
6. The generic Hermes topic is not a worker lane and must not pretend to be one.
7. If a machine/runtime query lands in the generic topic, Hermes must redirect to a dedicated lane or ask which lane to use.
8. Terse commands in dedicated lanes, including `pwd`, `whoami`, `hostname`, and `what agent oc now?`, must be treated as worker/runtime introspection requests first.
9. Every OpenCode worker response must start with the exact identity prefix format:

   `oc@vm_name@ip_address:`

10. Lane profiles are invalid unless they include `vm_name` and `ip_address`.
