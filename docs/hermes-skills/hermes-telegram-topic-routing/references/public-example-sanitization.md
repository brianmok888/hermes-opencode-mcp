# Public example sanitization for Hermes topic routing

Use this when publishing repo docs, templates, READMEs, or skills that show Telegram topic routing.

## Rule

Public examples must be generic and sanitized.

Do not publish deployment-specific:
- `chat_id`
- `topic_id`
- worker labels tied to real machines
- `target_id` values tied to private topology
- repo paths
- hostnames or IPs

## Good placeholder style

Prefer values like:
- `chat_id: <telegram_chat_id>`
- `topic_id: <coding_topic_id>`
- `topic_name: "Coding Worker"`
- `target_id: "coding-target"`
- `directory: "/path/to/coding-repo"`

## Avoid

Avoid values like:
- real supergroup IDs
- real forum topic IDs
- labels such as `VM02 OC Worker`
- target names derived from private machine names
- paths like `/srv/projects/<real-repo>`

## Scope

Apply this to:
- repo-local templates
- README snippets
- flow diagrams
- skill examples
- operator handoff docs

## Note

If a session starts with deployment-specific examples for speed, sanitize them before final commit/push if the artifact is public or reusable.
