# Install the exported Hermes skill

This repo includes a **sanitized export copy** of the Hermes skill:

- [`hermes-telegram-topic-routing/SKILL.md`](./hermes-telegram-topic-routing/SKILL.md)

Support files for the exported copy are here:

- [`hermes-telegram-topic-routing/references/public-example-sanitization.md`](./hermes-telegram-topic-routing/references/public-example-sanitization.md)
- [`hermes-telegram-topic-routing/references/repo-doc-handoff-pattern.md`](./hermes-telegram-topic-routing/references/repo-doc-handoff-pattern.md)
- [`hermes-telegram-topic-routing/references/repo-sanitization-checklist.md`](./hermes-telegram-topic-routing/references/repo-sanitization-checklist.md)

## What this is

This is a repo-local reference/export of a Hermes skill.

It is useful for:
- review
- documentation
- backup
- copying into a Hermes skill store
- giving an agent a stable file path to read before installation work

## What this is not

This repo copy does **not** automatically install itself into Hermes.
A Hermes runtime still needs the skill created in its skill store.

## Agent installation workflow

If an AI agent is asked to install or recreate this skill in Hermes, it should:

1. read [`./hermes-telegram-topic-routing/SKILL.md`](./hermes-telegram-topic-routing/SKILL.md)
2. read the linked reference files in the same directory if needed
3. create a Hermes skill named `hermes-telegram-topic-routing`
4. copy the sanitized markdown and support material into the Hermes skill store
5. verify the installed skill remains generic and contains no deployment-specific values

## Reusable agent prompt

Use this prompt when asking an agent to install the skill into Hermes:

```text
Install the Hermes skill exported in this repository at:
- docs/hermes-skills/hermes-telegram-topic-routing/SKILL.md

Also review these supporting references if needed:
- docs/hermes-skills/hermes-telegram-topic-routing/references/public-example-sanitization.md
- docs/hermes-skills/hermes-telegram-topic-routing/references/repo-doc-handoff-pattern.md
- docs/hermes-skills/hermes-telegram-topic-routing/references/repo-sanitization-checklist.md

Task requirements:
- Create or update a Hermes skill named `hermes-telegram-topic-routing`
- Preserve the architectural rule that Telegram topic routing belongs in Hermes, not in the MCP server
- Keep all examples generic and sanitized
- Do not introduce deployment-specific chat IDs, topic IDs, hostnames, target IDs, or repo paths into the exported/public copy
- Verify the installed skill is available after creation
```

## Repo-maintainer note

Keep this exported copy aligned with:
- [`../../TOPIC_ROUTING.md`](../../TOPIC_ROUTING.md)
- [`../../templates/topic-routing.example.yaml`](../../templates/topic-routing.example.yaml)
- [`../../templates/topic-routing.example.json`](../../templates/topic-routing.example.json)

If the Hermes skill changes materially, update this exported repo copy too.
