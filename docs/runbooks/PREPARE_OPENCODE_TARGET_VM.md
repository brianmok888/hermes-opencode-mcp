# Prepare OpenCode target VM

This runbook prepares a worker/target VM for use by `hermes-opencode-mcp`.

## Security and architecture rules

- SSH may be used for remote bootstrap only.
- SSH is not the default runtime execution architecture for this MCP service.
- The target must have a declared IP/address or hostname for MCP config.
- If auth exists for direct `opencode serve` handoff, keep token values only on the VM side.

## Shared prerequisites

Collect:
- VM type: `local network` or `remote`
- VM IP/address or hostname
- target repo path
- whether direct `opencode serve` metadata is desired
- optional auth env var name

## Path A: local-network VM

1. Reach the VM through your normal local-network admin path.
2. Install OpenCode CLI and required dependencies.
3. Ensure the target repo exists at the desired path.
4. Confirm the IP/address that should be recorded in MCP config.
5. If desired, prepare `opencode serve` on the VM side and record only metadata back to MCP.

## Path B: remote VM via SSH

1. Confirm SSH connectivity.
2. Use SSH for setup only.
3. Install OpenCode CLI and dependencies remotely.
4. Ensure the repo exists at the desired remote path.
5. If auth is needed, generate/store it on the VM side only. Example:

```bash
ssh <vm-host> 'openssl rand -hex 32'
```

6. Record only the env var name for metadata, not the token value.

## Validation checklist

- OpenCode CLI is installed on the target VM
- repo path is correct
- operator can provide the declared IP/address for MCP config
- optional direct serve URL is known if needed
- optional auth env var name is known if needed

## Hand back to control-plane setup

Provide these values to the control-plane/bootstrap workflow:
- `target_id`
- `vm_name`
- `ip_address`
- `repo_path`
- optional `opencode_base_url`
- optional `opencode_auth_token_env`
