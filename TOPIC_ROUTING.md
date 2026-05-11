# TOPIC_ROUTING

This document defines the recommended routing boundary for Telegram + Hermes + `hermes-opencode-mcp`.

## Decision

**Telegram topic ID -> MCP target ID routing belongs in Hermes, not in `hermes-opencode-mcp`.**

That means:
- Telegram-specific routing logic lives in Hermes
- MCP stays transport-agnostic
- `hermes-opencode-mcp` only receives explicit `target_id` requests

## Architecture

```text
Telegram message in topic/thread
-> Hermes reads chat_id + topic_id
-> Hermes maps topic_id to target_id
-> Hermes calls hermes-opencode-mcp with target_id
-> MCP executes on the mapped VM/target
-> Hermes returns the result to Telegram
```

## Why this boundary is better

### Hermes should own
- Telegram `chat_id`
- Telegram `message_thread_id` / topic ID
- topic-to-target policy
- operator access control
- chat UX
- follow-up questions when routing is ambiguous
- async polling / result formatting back into Telegram

### MCP should own
- target validation
- execution task lifecycle
- persistence
- cancellation
- one-task-per-target concurrency
- worker identity prefixing
- OpenCode execution

## What not to do

Do **not** put these into `hermes-opencode-mcp`:
- Telegram topic IDs
- Telegram chat IDs
- topic-specific response rules
- Telegram bot command behavior

Those are orchestration concerns, not execution concerns.

---

## Hermes routing config example

Use a config structure like this on the Hermes side.

### YAML example

```yaml
telegram:
  routing:
    default_behavior: hermes_chat
    open_topic_messages_as_tasks: true
    topic_to_target:
      - chat_id: -1001234567890
        topic_id: 101
        topic_name: "Coding Worker A"
        target_id: "coding-node-1"
        directory: "/path/to/coding-repo"
        mode: "worker"

      - chat_id: -1001234567890
        topic_id: 102
        topic_name: "Runtime Worker A"
        target_id: "runtime-node-1"
        directory: "/path/to/runtime-repo"
        mode: "worker"

      - chat_id: -1001234567890
        topic_id: 199
        topic_name: "General Hermes"
        mode: "hermes_only"
```

### JSON example

```json
{
  "telegram": {
    "routing": {
      "default_behavior": "hermes_chat",
      "open_topic_messages_as_tasks": true,
      "topic_to_target": [
        {
          "chat_id": -1001234567890,
          "topic_id": 101,
          "topic_name": "Coding Worker A",
          "target_id": "coding-node-1",
          "directory": "/path/to/coding-repo",
          "mode": "worker"
        },
        {
          "chat_id": -1001234567890,
          "topic_id": 102,
          "topic_name": "Runtime Worker A",
          "target_id": "runtime-node-1",
          "directory": "/path/to/runtime-repo",
          "mode": "worker"
        },
        {
          "chat_id": -1001234567890,
          "topic_id": 199,
          "topic_name": "General Hermes",
          "mode": "hermes_only"
        }
      ]
    }
  }
}
```

Repo-local copies of these examples are also available at:
- [`templates/topic-routing.example.yaml`](./templates/topic-routing.example.yaml)
- [`templates/topic-routing.example.json`](./templates/topic-routing.example.json)
- [`docs/TOPIC_ROUTING_FLOW.md`](./docs/TOPIC_ROUTING_FLOW.md)

---

## Meaning of fields

- `chat_id`: Telegram supergroup chat ID
- `topic_id`: Telegram forum topic ID / message thread ID
- `topic_name`: human-readable label for operators
- `target_id`: the target passed to `hermes-opencode-mcp`
- `directory`: default working directory Hermes should send with the task
- `mode`:
  - `worker` = route to MCP target execution
  - `hermes_only` = do not dispatch to MCP automatically

---

## Hermes routing behavior example

Pseudo-logic:

```python
if platform == "telegram":
    route = lookup_route(chat_id=chat_id, topic_id=topic_id)

    if route is None:
        handle_as_normal_hermes_chat()

    elif route["mode"] == "hermes_only":
        handle_as_normal_hermes_chat()

    elif route["mode"] == "worker":
        submit_task_to_mcp(
            target_id=route["target_id"],
            directory=route["directory"],
            text=user_message,
        )
```

---

## Recommended operator behavior

### In dedicated worker topics
Hermes should:
- assume the mapped `target_id`
- acknowledge submission quickly
- return task ID
- poll for completion
- post result back into the same topic

Example:

```text
User in topic 101:
fix the failing import and run tests
```

Hermes internal routing:

```text
chat_id=-1001234567890
topic_id=101
-> target_id=coding-node-1
-> directory=/path/to/coding-repo
```

Hermes MCP call payload:

```json
{
  "target_id": "coding-node-1",
  "directory": "/path/to/coding-repo",
  "text": "fix the failing import and run tests"
}
```

### In generic Hermes topics
Hermes should:
- stay conversational
- not pretend there is a bound worker
- ask which target to use if execution is needed

---

## Suggested Telegram UX

### Worker topics
Treat plain text as task input by default.

Examples:
- `check why tests are failing`
- `inspect the restart issue, no edits`
- `run the migration and summarize risk`

### Generic Hermes topic
Keep it as orchestration / coordination.

Examples:
- `list targets`
- `which VM should handle this?`
- `show status for task_abc123`
- `cancel task_abc123`

---

## Safety recommendations

1. Keep `target_id` explicit in Hermes config.
2. Keep dedicated worker topics mapped 1:1 to stable targets.
3. Do not silently fall back from a worker topic to generic chat if execution fails.
4. If no route exists, say so clearly.
5. If a route exists but MCP target is missing/not ready, report that explicitly.
6. Preserve thread/topic targeting when replying into Telegram.

---

## Minimal onboarding procedure

1. Install and verify `hermes-opencode-mcp`
2. Create valid MCP targets in `targets.json`
3. Decide Telegram topic-to-target mapping in Hermes
4. Add Hermes routing config
5. Test one dedicated topic
6. Test generic Hermes topic separately
7. Roll out additional topics only after success

---

## Example target names

Suggested stable naming style:

- `vm01-target`
- `vm02-target`
- `omniroute-target`
- `runtime-node-1`
- `coding-node-1`

Avoid encoding Telegram topic IDs into the MCP target names.

Bad:
- `topic-509-target`

Better:
- `vm01-target`

---

## Rule summary

### Hermes decides
- which topic is speaking
- which target that topic maps to
- whether the message is a task or ordinary chat

### MCP decides
- whether the target is valid
- whether the task can run
- how task state is persisted and reported
- what execution result comes back

---

## If routing must change later

Change Hermes config only.

Do **not** rewrite the MCP server just because:
- a Telegram topic was renamed
- a new worker topic was added
- a topic moved to another VM
- the platform later expands beyond Telegram
