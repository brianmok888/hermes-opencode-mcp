---
name: prepare-opencode-target-vm
version: 1.0.0
description: Prepare a local-network or remote target VM for hermes-opencode-mcp/OpenCode workflows without changing the runtime architecture.
triggers:
  - prepare target vm
  - install local network vm
  - install remote vm via ssh
  - opencode worker vm setup
---

# Prepare OpenCode target VM

Use this skill when preparing a worker/target VM that Hermes MCP will point at.

## Goals

1. Prepare the VM so it is a valid execution target.
2. Distinguish setup-time SSH/bootstrap from runtime execution architecture.
3. Record stable operator-facing metadata without storing secrets in repo config.

## Core rules

- SSH may be used for bootstrap/setup on remote VMs, but it is not the default runtime execution architecture for the MCP service.
- The MCP target config should contain the declared `ip_address` or hostname to use.
- Optional `opencode_base_url` and `opencode_auth_token_env` are metadata unless a dedicated serve-based executor mode is implemented later.
- Keep VM auth material on the VM side only.

## Branch A: local-network VM

1. Confirm the VM IP/address on the local network.
2. Install OpenCode CLI and any required runtime dependencies.
3. Confirm the repo path that tasks should use.
4. If direct endpoint metadata handoff is desired, confirm address/URL and any VM-side auth config without treating it as the primary MCP validation path.
5. Report back the declared IP/address, repo path, and optional metadata for the control-plane config.

## Branch B: remote VM via SSH

1. Confirm SSH host/user reachability.
2. Use SSH only for setup/bootstrap tasks.
3. Install OpenCode CLI and dependencies remotely.
4. Confirm the remote repo path.
5. If auth is needed, generate/store it on the VM side only, for example:

```bash
ssh <vm-host> 'openssl rand -hex 32'
```

6. Report back the declared IP/address, repo path, and optional metadata/env-var name for control-plane config.

## Verification

- OpenCode CLI exists on the target VM
- target repo path is correct
- operator can state the VM IP/address that should go into MCP config
- any direct serve metadata is documented without exposing raw tokens
- the target is ready to be represented as a stable MCP target

## Security checklist

- do not paste live token values into repo docs or `targets.json`
- use placeholders in public/exported examples
- do not blur bootstrap SSH usage into runtime architecture claims
- keep hostnames/paths generic in reusable skills/docs unless the file is explicitly local-only

## Related repo doc

- `docs/runbooks/PREPARE_OPENCODE_TARGET_VM.md`
