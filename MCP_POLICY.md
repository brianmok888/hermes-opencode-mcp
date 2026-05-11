# MCP execution target policy

## Scope

This file defines the non-optional behavior contract for MCP clients using dedicated OpenCode execution targets.

## Hard rules

1. This repo is MCP-native and receives already-resolved target requests from the caller.
2. Each target is bound to exactly one OpenCode execution target.
3. Target execution must go through the configured OpenCode CLI backend.
4. Do not use raw shell as the default replacement for target execution.
5. CLI-based `opencode run ...` is the supported execution backend for this repo.
6. Every execution result must start with the exact identity prefix format:

   `oc@vm_name@ip_address:`

7. Execution targets are invalid unless they include `vm_name` and `ip_address`.
8. Only one queued or running task may exist per target at a time.
9. Server state must be persisted under the configured state directory.
