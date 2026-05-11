# Repo sanitization checklist for Hermes topic-routing artifacts

Before commit/push, verify that public or reusable artifacts use generic placeholders.

## Check these artifact types

- README snippets
- install guides
- architecture docs
- skill exports
- YAML/JSON templates
- flow docs

## Remove or replace deployment-specific values

Replace:
- real `chat_id`
- real `topic_id`
- real hostnames
- real VM names
- real private IP addresses
- real repo paths
- target IDs tied to private topology
- worker labels that expose infra naming

With placeholders like:
- `<telegram_chat_id>`
- `<coding_topic_id>`
- `coding-target`
- `/path/to/coding-repo`
- `devbox-a`
- `10.0.0.10`

## Quick verification habit

Before final commit:
1. search the repo for old chat IDs, topic IDs, hostnames, IPs, and repo paths
2. read the rendered examples in markdown, YAML, and JSON
3. only then commit/push or rewrite history
