# Quickstart

Use this page when you want the shortest correct setup path for a new `hermes-opencode-mcp` deployment.

## Recommended order

1. **Prepare the target VM**
   - local-network VM or remote VM via SSH bootstrap
   - confirm VM IP/address
   - install OpenCode CLI and dependencies
   - confirm target repo path
   - optional direct endpoint metadata/auth-env name

   See:
   - `docs/runbooks/PREPARE_OPENCODE_TARGET_VM.md`
   - `docs/hermes-skills/prepare-opencode-target-vm/SKILL.md`

2. **Bootstrap the control-plane MCP service on the Hermes VM**
   - clone repo
   - install package/env
   - create env file
   - create `targets.json`
   - install/start systemd if desired
   - validate `health` and `list_targets`

   See:
   - `docs/runbooks/BOOTSTRAP_HERMES_MCP_ON_CONTROL_VM.md`
   - `docs/hermes-skills/bootstrap-hermes-opencode-mcp-on-control-vm/SKILL.md`

3. **Install/sync Hermes skills**
   - install repo-exported reviewed skills into `~/.hermes/skills/`
   - verify drift-free sync

   Commands:

   ```bash
   scripts/install_hermes_skill.sh prepare-opencode-target-vm
   scripts/install_hermes_skill.sh bootstrap-hermes-opencode-mcp-on-control-vm
   scripts/install_hermes_skill.sh operate-hermes-opencode-mcp
   scripts/install_hermes_skill.sh hermes-telegram-topic-routing
   scripts/check_hermes_skill_sync.sh prepare-opencode-target-vm
   scripts/check_hermes_skill_sync.sh bootstrap-hermes-opencode-mcp-on-control-vm
   scripts/check_hermes_skill_sync.sh operate-hermes-opencode-mcp
   scripts/check_hermes_skill_sync.sh hermes-telegram-topic-routing
   ```

   See:
   - `docs/hermes-skills/INSTALL_HERMES_SKILL.md`
   - `docs/hermes-skills/install-hermes-repo-exported-skill/SKILL.md`

4. **Configure Hermes routing if Telegram topics are involved**
   - keep topic routing in Hermes
   - map `chat_id` + `topic_id` to explicit `target_id`
   - do not put Telegram routing into the MCP server

   See:
   - `TOPIC_ROUTING.md`
   - `docs/hermes-skills/hermes-telegram-topic-routing/SKILL.md`

5. **Operate normally**
   - check service health
   - review targets
   - run/submit tasks
   - poll async work if needed
   - troubleshoot via sanitized logs/state

   See:
   - `docs/runbooks/OPERATE_HERMES_OPENCODE_MCP.md`
   - `docs/hermes-skills/operate-hermes-opencode-mcp/SKILL.md`

## Architecture reminders

- Hermes owns routing/orchestration
- MCP owns execution
- runtime remains OpenCode CLI-backed
- `ip_address` is declared config, not auto-detected
- optional `opencode_base_url` and `opencode_auth_token_env` are metadata only and should not be used as the primary MCP/CLI validation path unless a new executor mode is explicitly added

## Security reminders

- never store raw tokens in repo docs or `targets.json`
- keep auth values on VM/service side only
- store only env var names in target metadata
- keep exported skills sanitized and drift-checked

## Next stop

For the full map of runbooks and skills, see:
- `docs/RUNBOOK_AND_SKILL_INDEX.md`
