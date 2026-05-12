---
name: install-hermes-repo-exported-skill
version: 1.0.0
description: Install or sync sanitized repo-exported Hermes skills into the local Hermes skill store with drift checking.
triggers:
  - install hermes skill
  - sync hermes skill
  - check hermes skill drift
  - install exported skill
---

# Install Hermes repo-exported skill

Use this skill when a repository contains sanitized, git-tracked exports of Hermes skills and you want the local Hermes runtime to use that reviewed copy.

## Goals

1. Treat the repo-exported skill as the canonical reviewed source.
2. Install the skill into `~/.hermes/skills/` reproducibly.
3. Keep exported/public copies sanitized.
4. Verify the installed local skill matches the repo copy.

## Core rules

- Do not edit the installed local skill first and forget to sync the repo export.
- Do not commit raw secrets, bearer tokens, `.env` values, private IDs, private topology names, or operator home-directory paths into exported skill files.
- Treat the repo copy as the shareable/reviewable version and the local Hermes skill store as the runtime copy.

## Workflow

1. Identify the exported skill path under `docs/hermes-skills/<skill-name>/`.
2. Read the exported `SKILL.md` and any reference files.
3. Install the skill into the correct local destination under `~/.hermes/skills/`.
4. Run the drift check to verify the installed skill matches the repo export.
5. If the repo export changes later, re-sync and re-check.

## Commands

From the repo root:

```bash
scripts/install_hermes_skill.sh <skill-name>
scripts/check_hermes_skill_sync.sh <skill-name>
```

To force a re-copy:

```bash
scripts/sync_hermes_skill.sh <skill-name>
```

## Security checklist

- exported skill examples use placeholders only
- no live token values in markdown or reference files
- no private chat/topic IDs in public examples unless intentionally redacted placeholders are used
- no operator-local absolute paths unless they are generic placeholders
- verify any VM auth examples use placeholders such as `<generated-token>` or `***`

## Done criteria

A skill install is done when:
- the exported repo copy exists
- the local Hermes copy exists in `~/.hermes/skills/`
- the drift check reports the two copies are in sync
- the exported copy remains sanitized and safe to commit
