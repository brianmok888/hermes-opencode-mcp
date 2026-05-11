# Repo doc handoff pattern for Hermes topic routing

When a session produces reusable Hermes-side routing material, carry it in two places:

1. **Skill support files** for long-term reuse by future agents.
2. **Repo-local docs/templates** so maintainers can use the examples without opening Hermes skills.

## Good deliverables for this class of task

- a boundary doc such as `TOPIC_ROUTING.md`
- a YAML routing template
- a JSON routing template
- a small flow/architecture doc showing Telegram topic -> Hermes router -> MCP target -> execution
- README links pointing to all of the above

## Durable rule

For Telegram topic routing work, do not stop at prose-only explanation if the user asks to "update repo" or "patch docs". Also add concrete copyable examples and cross-links.

## Recommended sequencing

1. write the project doc that states the boundary decision
2. patch README/install docs to point to it
3. add copyable templates in both YAML and JSON when useful
4. add a small flow doc/diagram for operator orientation
5. review diff, then commit and push if requested

## Why this matters

A routing-boundary decision is easy to agree with conceptually but still awkward to implement later unless the repo includes:
- exact config shape
- exact field names
- a sample payload
- an at-a-glance flow diagram
