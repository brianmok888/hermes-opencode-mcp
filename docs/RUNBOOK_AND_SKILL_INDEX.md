# Runbook and skill index

This index helps operators and agents choose the right **repo-tracked runbook** and **Hermes skill** for each stage of the `hermes-opencode-mcp` workflow.

## Core principle

Use:
- **runbooks** for copy-paste operator execution and handoff
- **skills** for reusable Hermes/agent procedure memory

Both should stay aligned. The repo-exported skill copies under `docs/hermes-skills/` are the reviewed canonical versions that can be installed into `~/.hermes/skills/`.

## Quick chooser

| Situation | Use this runbook | Use this skill |
|---|---|---|
| Install or sync a Hermes skill from the repo export | `docs/hermes-skills/INSTALL_HERMES_SKILL.md` | `docs/hermes-skills/install-hermes-repo-exported-skill/SKILL.md` |
| Bootstrap `hermes-opencode-mcp` on the Hermes/control VM | `docs/runbooks/BOOTSTRAP_HERMES_MCP_ON_CONTROL_VM.md` | `docs/hermes-skills/bootstrap-hermes-opencode-mcp-on-control-vm/SKILL.md` |
| Prepare a worker/target VM on LAN or remote SSH | `docs/runbooks/PREPARE_OPENCODE_TARGET_VM.md` | `docs/hermes-skills/prepare-opencode-target-vm/SKILL.md` |
| Operate a running deployment day-to-day | `docs/runbooks/OPERATE_HERMES_OPENCODE_MCP.md` | `docs/hermes-skills/operate-hermes-opencode-mcp/SKILL.md` |
| Route Telegram topics to MCP targets from Hermes | `TOPIC_ROUTING.md` | `docs/hermes-skills/hermes-telegram-topic-routing/SKILL.md` |
| Port/extend bridge-era behavior into MCP without breaking architecture | repo docs + install/release docs as needed | `docs/hermes-skills/port-hermes-opencode-bridge-to-mcp/SKILL.md` |

## Workflow by phase

### 1. Skill installation / synchronization

Use when:
- a new machine needs the same Hermes skills
- the repo-exported skill changed
- you want drift-free local Hermes behavior

Primary assets:
- `docs/hermes-skills/INSTALL_HERMES_SKILL.md`
- `scripts/install_hermes_skill.sh`
- `scripts/sync_hermes_skill.sh`
- `scripts/check_hermes_skill_sync.sh`
- skill: `install-hermes-repo-exported-skill`

### 2. Control-plane bootstrap

Use when:
- the Hermes/control VM needs a fresh MCP install
- you are setting up systemd, env files, or targets config
- you are onboarding a new control VM

Primary assets:
- `docs/runbooks/BOOTSTRAP_HERMES_MCP_ON_CONTROL_VM.md`
- `INSTALL_AND_RELEASE.md`
- `deploy/systemd/hermes-opencode-mcp.service`
- `deploy/env/hermes-opencode-mcp.env.example`
- skill: `bootstrap-hermes-opencode-mcp-on-control-vm`

### 3. Target VM preparation

Use when:
- a local-network VM needs to become an execution target
- a remote VM needs bootstrap via SSH
- you need to capture VM IP/address, repo path, or optional serve metadata

Primary assets:
- `docs/runbooks/PREPARE_OPENCODE_TARGET_VM.md`
- skill: `prepare-opencode-target-vm`

### 4. Day-2 / normal operations

Use when:
- the MCP service is already deployed
- you need health checks, target review, execution, troubleshooting, or handoff

Primary assets:
- `docs/runbooks/OPERATE_HERMES_OPENCODE_MCP.md`
- skill: `operate-hermes-opencode-mcp`

### 5. Telegram routing boundary

Use when:
- Hermes needs to map Telegram topic traffic to explicit MCP targets
- you need to preserve the separation between control-plane routing and execution plane

Primary assets:
- `TOPIC_ROUTING.md`
- `templates/topic-routing.example.yaml`
- `templates/topic-routing.example.json`
- skill: `hermes-telegram-topic-routing`

### 6. Bridge-to-MCP porting / architectural extension

Use when:
- porting old bridge workflows into MCP-native structure
- absorbing durable lessons into repo/docs/skills
- preserving CLI-backed execution while documenting additional metadata/ops patterns

Primary assets:
- skill: `port-hermes-opencode-bridge-to-mcp`
- `README.md`
- `INSTALL_AND_RELEASE.md`
- exported references under `docs/hermes-skills/port-hermes-opencode-bridge-to-mcp/references/`

## Recommended operator order

For a fresh deployment, usually follow this order:

1. Install/sync the needed Hermes skills
2. Prepare the target VM
3. Bootstrap the control-plane MCP service on the Hermes VM
4. Configure Hermes topic routing if needed
5. Run day-2 operations using the operations runbook/skill

## Security reminders

- repo-exported skill copies must stay sanitized
- do not commit raw secrets or live auth tokens
- keep token values only on VM/service side
- store only env var names in target metadata
- do not blur SSH bootstrap into runtime architecture

## Handy commands

Install a skill:

```bash
scripts/install_hermes_skill.sh <skill-name>
```

Check drift:

```bash
scripts/check_hermes_skill_sync.sh <skill-name>
```

Resync:

```bash
scripts/sync_hermes_skill.sh <skill-name>
```
