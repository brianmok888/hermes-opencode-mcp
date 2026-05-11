# TOPIC_ROUTING_FLOW

Small reference diagram for the Telegram topic -> Hermes router -> MCP target flow.

## Diagram

```text
Telegram supergroup
└─ topic/thread message
   ├─ chat_id = -1001234567890
   └─ topic_id = 101
              |
              v
        Hermes router
        - reads chat_id + topic_id
        - looks up route table
        - decides chat vs task
              |
              v
     route match: topic_id 101
        -> target_id=coding-node-1
        -> directory=/path/to/coding-repo
              |
              v
      hermes-opencode-mcp
      - validate target_id
      - submit task
      - persist task state
      - enforce concurrency
              |
              v
        OpenCode CLI
              |
              v
      execution result
              |
              v
        Hermes posts reply
      back into same topic
```

## Rule of thumb

- Hermes owns Telegram awareness
- MCP owns execution awareness
- OpenCode performs the actual task execution

## Boundary summary

### Hermes knows
- `chat_id`
- `topic_id`
- topic labels
- whether plain text should be treated as a task
- where to send the result back

### MCP knows
- `target_id`
- execution directory
- task lifecycle
- cancellation and status
- worker result formatting

## Example

```text
Telegram topic 101
-> Hermes route lookup
-> coding-node-1
-> hermes-opencode-mcp submit_task
-> OpenCode runs task
-> Hermes sends result to topic 101
```

## Related files

- [`../TOPIC_ROUTING.md`](../TOPIC_ROUTING.md)
- [`../templates/topic-routing.example.yaml`](../templates/topic-routing.example.yaml)
- [`../templates/topic-routing.example.json`](../templates/topic-routing.example.json)
