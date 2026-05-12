# Install exported Hermes skills

This repo includes **sanitized, git-tracked export copies** of Hermes skills so the repo can act as the canonical reviewed source.

## Available exported skills

- [`hermes-telegram-topic-routing/SKILL.md`](./hermes-telegram-topic-routing/SKILL.md)
- [`port-hermes-opencode-bridge-to-mcp/SKILL.md`](./port-hermes-opencode-bridge-to-mcp/SKILL.md)
- [`install-hermes-repo-exported-skill/SKILL.md`](./install-hermes-repo-exported-skill/SKILL.md)
- [`bootstrap-hermes-opencode-mcp-on-control-vm/SKILL.md`](./bootstrap-hermes-opencode-mcp-on-control-vm/SKILL.md)
- [`prepare-opencode-target-vm/SKILL.md`](./prepare-opencode-target-vm/SKILL.md)
- [`operate-hermes-opencode-mcp/SKILL.md`](./operate-hermes-opencode-mcp/SKILL.md)

## Security rules for exported skills

- Exported skills must remain generic and sanitized.
- Do not commit raw secrets, bearer tokens, API keys, `.env` values, private chat IDs, private topic IDs, private hostnames, or operator home-directory paths unless they are already intentionally public placeholders.
- Auth examples must use placeholders such as `<generated-token>` or `***`, not live values.
- Repo copies are for review, versioning, installation, and drift detection.

## What this is

This directory is a repo-local, versioned source for Hermes skills.

It is useful for:
- review in git
- backup and handoff
- reproducible installation into `~/.hermes/skills/`
- drift detection between repo and installed local skill copies

## What this is not

These repo copies do **not** auto-install themselves into Hermes.
A Hermes runtime still needs the skill material copied into its local skill store.

## Install one exported skill

Use the install script from the repo root:

```bash
scripts/install_hermes_skill.sh port-hermes-opencode-bridge-to-mcp
scripts/install_hermes_skill.sh bootstrap-hermes-opencode-mcp-on-control-vm
scripts/install_hermes_skill.sh prepare-opencode-target-vm
scripts/install_hermes_skill.sh operate-hermes-opencode-mcp
scripts/install_hermes_skill.sh install-hermes-repo-exported-skill
scripts/install_hermes_skill.sh hermes-telegram-topic-routing
```

## Verify installed skill matches repo copy

```bash
scripts/check_hermes_skill_sync.sh port-hermes-opencode-bridge-to-mcp
scripts/check_hermes_skill_sync.sh bootstrap-hermes-opencode-mcp-on-control-vm
scripts/check_hermes_skill_sync.sh prepare-opencode-target-vm
scripts/check_hermes_skill_sync.sh operate-hermes-opencode-mcp
scripts/check_hermes_skill_sync.sh install-hermes-repo-exported-skill
scripts/check_hermes_skill_sync.sh hermes-telegram-topic-routing
```

## Force resync repo copy into the Hermes skill store

```bash
scripts/sync_hermes_skill.sh port-hermes-opencode-bridge-to-mcp
scripts/sync_hermes_skill.sh bootstrap-hermes-opencode-mcp-on-control-vm
scripts/sync_hermes_skill.sh prepare-opencode-target-vm
scripts/sync_hermes_skill.sh operate-hermes-opencode-mcp
scripts/sync_hermes_skill.sh install-hermes-repo-exported-skill
scripts/sync_hermes_skill.sh hermes-telegram-topic-routing
```

## Agent installation workflow

If an AI agent is asked to install or recreate one of these skills in Hermes, it should:

1. read the exported `SKILL.md`
2. read linked reference files in the same exported directory if needed
3. create or update the Hermes skill under the correct local category path
4. copy only sanitized repo-tracked content into the Hermes skill store
5. verify the installed skill matches the repo export

## Reusable agent prompt

```text
Install the Hermes skill exported in this repository.

Inputs:
- skill name: <skill-name>
- exported skill path: docs/hermes-skills/<skill-name>/SKILL.md

Task requirements:
- Create or update the Hermes skill using the repo-exported copy as the canonical source
- Copy any exported reference files from docs/hermes-skills/<skill-name>/references/
- Preserve architecture and security rules described in the skill
- Keep public/exported copies sanitized
- Do not introduce deployment-specific secrets, private IDs, private topology names, or operator home paths into the repo copy
- Verify the installed local Hermes skill matches the repo export after installation
```

## Repo-maintainer note

When a local Hermes skill changes materially, update the exported repo copy and re-run the sync/check flow. Treat the repo export as the reviewed, shareable version.
