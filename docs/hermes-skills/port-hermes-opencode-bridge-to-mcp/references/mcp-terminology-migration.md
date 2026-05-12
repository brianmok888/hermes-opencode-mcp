# MCP terminology migration: lane -> execution target

Use this when a first-pass MCP port preserved legacy `lane` naming but the user later wants a stricter public API.

## Rename set

Apply the rename consistently across the whole repo:

- `LaneProfile` -> `ExecutionTarget`
- `LaneService` -> `ExecutionService`
- `lane_id` -> `target_id`
- `list_lanes` -> `list_targets`
- `get_lane` -> `get_target`
- `HERMES_MCP_LANES_FILE` -> `HERMES_MCP_TARGETS_FILE`
- `templates/lanes.example.json` -> `templates/targets.example.json`
- wording in README/policy/resources/prompts: `lane` -> `target` where it is part of the public MCP contract

## What to update together

1. Data models and type aliases.
2. Config loading and validation errors.
3. In-memory store method names.
4. MCP service/tool schema and prompt argument names.
5. Client helper methods and submit/wait wrappers.
6. Templates/resources/docs.
7. Tests and fixtures.

## Verification

1. Search for leftovers before running tests:
   - `lane`, `LaneService`, `LaneProfile`, `lane_id`, `list_lanes`, `get_lane`, old env var, old template name.
2. Run the targeted test suite or `pytest -q`.
3. Confirm public examples use only the new names.

## Pitfall

Do not stop after renaming only the MCP tool names. A mixed API (`get_target` with `lane_id`, or `ExecutionService` still reading `HERMES_MCP_LANES_FILE`) creates a worse migration surface than either consistent old naming or consistent new naming.
