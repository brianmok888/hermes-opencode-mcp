---
name: port-hermes-opencode-bridge-to-mcp
version: 1.0.0
description: Port a Hermes OpenCode bridge repo into an MCP-native repo while preserving lane/task semantics, worker identity guarantees, and CLI-backed execution.
triggers:
  - port opencode bridge to mcp
  - migrate hermes bridge to mcp
  - build mcp-native opencode server
  - convert aiohttp bridge to mcp
---

# Port Hermes OpenCode bridge to MCP

Use this skill when an existing Hermes/OpenCode bridge repo needs to be ported into a new MCP-native repository.

## Goals

1. Preserve the execution contract.
2. Preserve task lifecycle semantics.
3. Preserve worker identity prefix enforcement.
4. Move transport concerns from HTTP bridge endpoints to MCP tools/resources/prompts.
5. Keep OpenCode CLI execution as the backend unless the user explicitly wants an SDK/runtime API.
6. When the user wants stricter MCP terminology, rename public "lane" concepts to neutral execution-target terminology consistently across API, docs, tests, and client helpers.
7. In Telegram-facing/user-facing language for this workflow, prefer **OC Worker topic** / **Omni OC Worker topic** over `lane` or generic `worker topic` when referring to dedicated OpenCode-only topics.
8. If bridge-era capabilities are discussed but should not be revived as MCP runtime behavior yet, still absorb the durable parts into the MCP repo as schema/docs/operator-facing metadata instead of leaving them only in chat. Example: direct `opencode serve` endpoint info and per-target auth-env naming can live in target metadata and docs even while execution remains CLI-backed.

## Core rule

Do **not** silently change the execution model from OpenCode CLI to raw shell. The MCP repo should still use the OpenCode bridge to execute tasks on VM02 or other mapped workers instead of treating SSH/shell as the primary worker path.

## Porting checklist

1. Inspect the source repo first:
   - `models.py`
   - `config.py`
   - `store.py`
   - `executor.py` / adapter layer
   - server/router/client helpers
   - docs and policy files
2. Identify which features are transport-specific versus domain-specific.
3. Create the new repo with `src/<package>/`, `tests/`, `templates/`, docs, and packaging metadata.
4. Port the domain layer first:
   - lane profiles
   - task records
   - cancellation state
   - metadata
   - sanitization
   - worker prefix enforcement
5. Port execution second:
   - keep `opencode run --pure --format json --dir ...`
   - parse streamed JSON text events
   - capture `sessionID`
   - preserve timeout/cancel behavior
6. Replace HTTP endpoints with MCP surfaces:
   - health/list/get/create/submit/run/cancel/artifacts as tools
   - policy/template/architecture as resources
   - common workflows as prompts
7. Add a small client helper if Hermes-side integration still needs submit/poll ergonomics.
8. Add route-table loading only if topic-to-lane mapping remains outside the MCP server.
9. Before any commit/push, confirm the active repo/root explicitly when both the old bridge repo and the new MCP repo exist side-by-side. Check `pwd`, `git remote -v`, branch, and uncommitted diff in the intended repo so you do not accidentally commit to the deprecated bridge repo after context compression or session handoff.
10. Verify imports, task lifecycle, MCP initialize/list/call flows, and client round-trip.
11. Update docs to explain what stayed in Hermes versus what moved into the MCP server.
12. If the user wants the MCP repo to become the single source of truth, migrate any still-useful bridge operational assets (provisioning helper, onboarding notes, worker policy, decommissioning notes) into the MCP repo under docs/scripts before deleting the old bridge repo.
13. If the user explicitly says to remove legacy tracks after the MCP port is feature-complete, do a second-pass cutover cleanup:
   - compare the archived bridge repo against the active MCP package and keep only functionality still needed at runtime
   - remove legacy docs/scripts/templates/archive content that exists only for bridge migration history
   - run a repo-wide residual search for legacy markers (`bridge`, old env var prefixes, archived package names, obsolete template names, old conceptual terms) outside `.git/`, `.venv/`, and `__pycache__`
   - review `git status --short` / `git ls-files` so you know exactly which tracked legacy paths are being removed
   - update README/install docs so they no longer advertise preserved legacy tracks if those tracks were deleted
   - only then commit and push the cleanup

## Recommended MCP mapping

Choose one terminology set early and keep it consistent. If the user asks for a stricter public MCP surface, prefer `target` naming everywhere instead of mixing `lane` and `target`.

### Tools

At minimum expose either the legacy lane set or the stricter target set:
- `health`
- `list_targets` / `list_lanes`
- `get_target` / `get_lane`
- `create_task`
- `submit_task`
- `get_task`
- `cancel_task`
- `get_artifacts`
- `run_task`

### Resources

Usually expose:
- architecture overview
- worker policy
- example target config

### Prompts

Usually expose:
- coding-task
- runtime-check

## Behavior that must be preserved

- lane profiles require `vm_name` and `ip_address`
- every worker response must begin with `oc@vm_name@ip_address:`
- `dispatch_status` must reach a terminal value for completed/failed/cancelled tasks
- metadata should retain `execution_handle`, `worker_prefix`, timeout/agent/session info
- cancellation before dispatch and during execution should remain distinguishable
- output must be sanitized before being returned
- startup reconciliation must convert persisted `queued`/`running` tasks into an explicit terminal state after restart rather than leaving them stuck indefinitely
- production logging should be structured and retention-safe: log task IDs, target IDs, lengths, statuses, execution handles, and recovery counts, but do not log full task prompts or full execution output by default

## Production-hardening add-ons

After the core port works, a production-ready pass should usually add these pieces together rather than as disconnected follow-ups:

1. **Operational packaging**
   - add a systemd unit under `deploy/systemd/`
   - add an env-file template under `deploy/env/`
   - wire restart policy, working directory, `EnvironmentFile=`, and restricted write paths
2. **Structured logging**
   - add a lightweight logging module and configure it from env (`LOG_LEVEL`, `LOG_JSON` style flags)
   - default to JSON logs on stderr/journald
   - emit metadata-only task lifecycle events (`task_created`, `task_running`, `task_terminal`, recovery/cancel events, RPC request/error events)
3. **Restart recovery**
   - on service startup, reconcile persisted in-flight tasks (`queued`/`running`) into terminal `failed` with a machine-readable marker such as `dispatch_status=interrupted_on_startup`
   - expose the recovery count in `health` so operators can see that restart cleanup occurred
4. **Real E2E verification**
   - add a runnable script that starts the server with real env, submits a task through the client/helper, waits for terminal state, and prints a JSON report
   - keep this distinct from unit tests: unit tests prove contract shape, live E2E proves real OpenCode target wiring
5. **Operator handoff docs**
   - add a dedicated `INSTALL_AND_RELEASE.md` when the user wants a copy-paste onboarding/install/run/release playbook
   - write it for an AI agent or operator, not as marketing docs: preflight, clone, venv, env file, targets file, manual run, pytest, optional live E2E, systemd install, then commit/merge/push
   - prefer exact commands and explicit validation checkpoints after each stage
   - for this user, simplify installation instructions rather than re-explaining architecture; the desired artifact is a step-by-step operational runbook
6. **Provisioning/bootstrap helper**
   - when the deployed bridge needs repeatable token sync + service rendering across Hermes and remote workers, add a checked-in helper script under `scripts/` rather than leaving it as a local-only scratch command
   - for this workflow, keep the runtime rule strict: the MCP server itself should read a declared `ip_address` from target config and should not infer or auto-discover network identity during normal execution
   - if install/bootstrap needs network info, collect it from the operator at install time: ask whether the VM is on the local network or remote, then ask for the IP/address to write into target config or env files
   - if direct endpoint auth is needed, include an operator step that first confirms the VM already has the auth-bearing environment or service config that `opencode serve` will read
   - then let the user SSH to the VM and generate the token there (for example `ssh <vm-host> 'openssl rand -hex 32'`), store the token only in the VM-side env/service config, and record only the env-var name in config/docs
   - when helpful, document a tiny VM-side env snippet (for example `OPENCODE_AUTH_TOKEN=<generated-token>` or `VM02_OPENCODE_TOKEN=<generated-token>`) while keeping raw token values out of repo config, checked-in docs, and MCP target JSON
   - when documenting this flow, prefer explicit install questionnaires and concrete config snippets over abstract prose; this user wants operational decisions folded directly into repo docs/skills, not left only in chat
   - document the helper briefly in `README.md` so future operators know it exists and when to use it
   - if the bridge repo is being retired, preserve this helper in the MCP repo as a migration/decommissioning asset and label it clearly as legacy bridge operations support rather than as the new runtime architecture

See `references/mcp-production-hardening.md` for the concrete pattern added in this session.
See `references/bridge-provisioning-helper-pattern.md` for the provisioning-helper pattern and output contract.
See `references/bridge-capability-adoption-without-runtime-revival.md` for how to preserve bridge-era operational knowledge as MCP schema/docs/tests without reintroducing the old bridge runtime.
See `references/canonical-repo-cutover.md` for the side-by-side bridge→MCP cutover checklist when both repos still exist.
See `references/legacy-track-removal-after-port.md` for the post-port cleanup pass when the user wants all legacy tracks removed from the canonical MCP repo.

## Verification strategy

Prefer this order:

1. import sanity
2. adapter parse sanity
3. service-level mock execution
4. MCP `initialize`
5. MCP `tools/list`
6. MCP `tools/call`
7. client subprocess round-trip over stdio
8. test file compile sanity
9. full `pytest` if the environment supports it
10. repo sanitize/security audit before shipping

### Post-port sanitize/security audit

Before calling the port done, run a quick repo-wide audit:

- search for obvious secrets or auth material in tracked files
- review `sanitize_text()` coverage, not just whether it exists
- verify sanitizer is used on adapter output, service error paths, and client-side surfaced errors
- confirm `.gitignore` covers `.env`, logs, caches, temp state, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, and `*.egg-info/`
- untrack generated packaging metadata if it was created during editable installs/builds (`src/*.egg-info/` should not be committed)
- check `git status --short --ignored` so ignored junk is distinguished from accidentally tracked junk

A passing test suite is not enough if the repo still tracks generated metadata or has weak redaction coverage.

If `pytest` or `python3-venv` is unavailable, do not loop on the same failing install command repeatedly. Switch to direct import/runtime validation and report the environment limitation clearly.

When `uv` is available, prefer it for the final real test pass:

```bash
uv venv --clear
. .venv/bin/activate
uv pip install -e .[dev]
pytest -q
```

This is the preferred recovery path when the base OS Python lacks `venv` convenience or global `pytest`.

## Environment pitfalls

- Debian/Ubuntu boxes may lack `python3-venv`
- `pytest` may not be globally installed
- generated Python files can accidentally contain broken multiline string literals when produced programmatically; re-read and fix before continuing
- editable installs/build steps can generate `src/*.egg-info/`; add `*.egg-info/` to `.gitignore` early and remove tracked egg-info before shipping

## Implementation notes

- Keep topic ID to lane ID routing in Hermes unless the user explicitly wants it embedded into the server.
- If the old bridge had async submit+poll semantics, preserve them with `submit_task` + `get_task` even if `run_task` also exists.
- Model artifacts now even if collection is minimal; this avoids reshaping the API later.
- A lightweight handwritten stdio MCP server is acceptable for a first pass if no MCP SDK is installed.
- If the user requests stricter terminology cleanup after an initial port, do a repo-wide rename pass instead of partial aliases: models, config keys, store methods, service class names, MCP tool names, prompt arguments, templates, README/policy text, tests, and client helper methods should all move together.
- After a terminology migration, run a repo-wide search for leftovers such as `LaneService`, `LaneProfile`, `lane_id`, `list_lanes`, `get_lane`, old env vars, and old template names before declaring done.
- If you learn a better way during the task, embed the lesson into this skill instead of leaving it only in the chat.
- See `references/uv-test-and-git-cleanup.md` for the preferred uv-based test pass and pre-commit cleanup checklist.
- See `references/mcp-terminology-migration.md` for a concrete lane→target rename checklist.
- See `references/install-and-release-runbook-pattern.md` for the operator/AI-agent handoff doc pattern when the user wants a dedicated install/run/release playbook.

## Done criteria

A port is complete when:
- the new repo exists and is runnable
- MCP tools/resources/prompts are implemented
- OpenCode CLI execution path is preserved
- worker prefix contract is enforced
- client/helper integration works end-to-end
- tests or equivalent runtime verification pass
- docs explain architecture and usage
