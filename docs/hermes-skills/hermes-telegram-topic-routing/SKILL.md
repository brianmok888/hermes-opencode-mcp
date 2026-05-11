---
name: hermes-telegram-topic-routing
version: 1.0.0
description: Route Telegram forum topics to MCP/OpenCode targets from Hermes while keeping execution servers transport-agnostic.
triggers:
  - telegram topic routing
  - topic_id to target_id
  - hermes telegram mcp routing
  - telegram forum topics
  - hermes opencode mcp
  - topic to worker mapping
---

# Hermes Telegram Topic Routing

Use this skill when Hermes needs to decide whether a Telegram topic message should stay in normal chat flow or be dispatched to a specific MCP/OpenCode execution target.

## Core rule

**Telegram topic ID -> target ID routing belongs in Hermes, not in the MCP server.**

Hermes is the orchestration/control plane.
The MCP server is the execution plane.

## Keep responsibilities separate

### Hermes owns
- Telegram `chat_id`
- Telegram `message_thread_id` / `topic_id`
- topic-to-target mapping policy
- operator UX and fallback behavior
- deciding whether plain text in a topic is chat or task input
- async polling and posting results back into the same Telegram topic
- access control and topic-level restrictions

### MCP/OpenCode backend owns
- validating `target_id`
- task submission/status/cancellation
- worker concurrency limits
- persistence
- execution proof and worker identity prefixing
- actual OpenCode/task execution

## Do not put these in the MCP server

- Telegram `topic_id`
- Telegram `chat_id`
- Telegram-specific command routing
- Telegram response policy by topic
- bot UX rules

If those leak into the execution server, the server becomes Telegram-coupled and harder to reuse from other clients.

## Recommended config shape in Hermes

Use an explicit route table keyed by Telegram `chat_id` + `topic_id`.

Support files in this exported repo copy:
- `templates/topic-routing.example.yaml`
- `templates/topic-routing.example.json`
- `references/public-example-sanitization.md`
- `references/repo-doc-handoff-pattern.md`
- `references/repo-sanitization-checklist.md`

Example YAML:

```yaml
telegram:
  routing:
    default_behavior: hermes_chat
    open_topic_messages_as_tasks: true
    topic_to_target:
      - chat_id: <telegram_chat_id>
        topic_id: <coding_topic_id>
        topic_name: "Coding Worker"
        target_id: "coding-target"
        directory: "/path/to/coding-repo"
        mode: "worker"

      - chat_id: <telegram_chat_id>
        topic_id: <runtime_topic_id>
        topic_name: "Runtime Worker"
        target_id: "runtime-target"
        directory: "/path/to/runtime-repo"
        mode: "worker"

      - chat_id: <telegram_chat_id>
        topic_id: <general_topic_id>
        topic_name: "General Coordination"
        mode: "hermes_only"
```

When examples are intended for public docs or reusable templates, sanitize them fully: use generic placeholders and avoid deployment-specific chat IDs, topic IDs, hostnames, target IDs, repo paths, or worker labels.

## Field meanings

- `chat_id`: Telegram chat/container ID from the incoming event
- `topic_id`: Telegram message thread/topic ID
- `topic_name`: human-readable operator label
- `target_id`: the exact target to send to MCP/OpenCode
- `directory`: default working directory for task execution
- `mode`:
  - `worker` -> Hermes dispatches to MCP/OpenCode
  - `hermes_only` -> Hermes stays conversational and does not auto-dispatch

## Routing algorithm

1. Read platform, `chat_id`, and `topic_id` from the incoming message.
2. Look up a route using `chat_id` + `topic_id`.
3. If no route exists, keep the message on the normal Hermes path.
4. If route mode is `hermes_only`, keep the message on the normal Hermes path.
5. If route mode is `worker`, construct an explicit MCP request using the mapped `target_id` and default `directory`.
6. Return submission status quickly, then poll and reply into the same topic.

Pseudo-code:

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
            directory=route.get("directory"),
            text=user_message,
        )
```

## UX rules

### Dedicated worker topics
- treat plain text as task input by default
- assume the mapped target unless the user explicitly overrides
- return a task ID or clear blocker
- post final results back into the same topic
- do not pretend a task ran if dispatch never happened

### Generic Hermes topics
- stay conversational
- do not pretend there is a bound worker
- ask which target to use when execution is required
- keep coordination commands like `list targets`, `status`, and `cancel` here

## Safety rules

1. Keep `target_id` explicit in Hermes config.
2. Map dedicated worker topics 1:1 to stable targets where possible.
3. Do not silently fall back from a worker topic to generic chat when execution fails.
4. If no route exists, say so clearly.
5. If the route exists but the target is missing/unready, report that explicitly.
6. Preserve Telegram thread targeting on every reply.
7. Do not encode Telegram topic IDs into target names; keep target names stable and platform-agnostic.

## Good target naming

For real deployments, prefer stable platform-agnostic names such as:
- `vm01-target`
- `vm02-target`
- `omniroute-target`
- `coding-node-1`
- `runtime-node-1`

For public docs, reusable templates, and skills, prefer fully generic placeholders such as:
- `coding-target`
- `runtime-target`
- `<telegram_chat_id>`
- `<coding_topic_id>`

Avoid:
- `topic-509-target`
- `thread-3-worker`
- deployment-specific machine labels or private topology names in published examples

## Verification checklist

After wiring routing:

1. verify Hermes can read `chat_id` and `topic_id`
2. verify route lookup selects the expected `target_id`
3. verify a `hermes_only` topic does not dispatch
4. verify a worker topic produces an MCP submit request with explicit `target_id`
5. verify the final response returns to the same Telegram topic
6. verify unknown topics stay on the normal Hermes path
7. verify missing/unready targets produce explicit operator-facing errors

## Design summary

### Hermes decides
- which Telegram topic is speaking
- whether the input is chat or task
- which target the topic maps to
- how the result is surfaced back to Telegram

### MCP decides
- whether the target is valid
- whether execution can start
- how task state is stored and reported
- what execution result comes back

## Related doc

If you created project-local documentation for this setup, keep a companion doc such as `TOPIC_ROUTING.md` in the repo so maintainers can see the boundary decision without loading this skill first.
