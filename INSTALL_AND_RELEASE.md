# INSTALL_AND_RELEASE

This file is written for an AI agent or operator to follow exactly.

Goal:
- install `hermes-opencode-mcp`
- configure it
- run it
- verify it
- optionally install it as a systemd service
- commit, merge, and push changes

---

## 0. What this project is

`hermes-opencode-mcp` is a stdio MCP server.

Typical flow:

```text
Telegram -> Hermes -> MCP -> OpenCode execution target
```

This repo itself is the MCP layer. It expects:
- Python 3.12+
- an `opencode` binary available on PATH
- a targets JSON file
- a writable state directory

---

## 1. Preflight checks

Run these first:

```bash
python3.12 --version || python3 --version
command -v git
command -v opencode
```

Expected:
- Python is available
- Git is available
- `opencode` resolves on PATH

If `opencode` is missing, stop and install/configure OpenCode first.

---

## 2. Clone the repository

```bash
git clone https://github.com/brianmok888/hermes-opencode-mcp.git
cd hermes-opencode-mcp
```

Verify:

```bash
git status --short --branch
```

Expected: clean checkout on `main`.

---

## 3. Create a virtual environment and install the package

```bash
python3.12 -m venv .venv || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Verify:

```bash
python -m hermes_opencode_mcp --help >/dev/null 2>&1 || true
python -c "import hermes_opencode_mcp; print('import ok')"
```

Expected:
- package installs without error
- import succeeds

---

## 4. Create required directories

For a production-style layout:

```bash
sudo install -d /opt/hermes-opencode-mcp
sudo install -d /etc/hermes-opencode-mcp
sudo install -d /var/lib/hermes-opencode-mcp
```

If running directly from the git checkout, `/opt/hermes-opencode-mcp` is optional.

---

## 5. Prepare the targets file

Use the example as a base:

```bash
cp templates/targets.example.json /tmp/targets.example.json
cat /tmp/targets.example.json
```

Create the real file:

```bash
sudo tee /etc/hermes-opencode-mcp/targets.json >/dev/null <<'JSON'
[
  {
    "target_id": "coding-node-1",
    "node_id": "node-1",
    "hostname": "vm02",
    "vm_name": "vm02",
    "ip_address": "192.168.4.82",
    "role": "coding-node",
    "repo_path": "/path/to/repo/on/target",
    "opencode_ready": true
  }
]
JSON
```

Rules:
- `target_id` must be unique
- `vm_name` is required
- `ip_address` is required
- `repo_path` must be correct for the execution target
- `opencode_ready` should be `true` only when that target is actually usable

Verify JSON:

```bash
python - <<'PY'
import json
p='/etc/hermes-opencode-mcp/targets.json'
with open(p,'r',encoding='utf-8') as f:
    data=json.load(f)
assert isinstance(data,list) and data, 'targets file must be a non-empty list'
print('targets ok:', len(data))
PY
```

---

## 6. Create the environment file

Copy the example:

```bash
sudo cp deploy/env/hermes-opencode-mcp.env.example /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
```

Edit it so the paths match the real machine:

```bash
sudoedit /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
```

Recommended contents:

```bash
PYTHONPATH=/absolute/path/to/hermes-opencode-mcp/src
HERMES_MCP_TARGETS_FILE=/etc/hermes-opencode-mcp/targets.json
HERMES_MCP_EXECUTOR=opencode
HERMES_MCP_OPENCODE_BIN=opencode
HERMES_MCP_REPO_ROOT=/absolute/path/to/hermes-opencode-mcp
HERMES_MCP_STATE_DIR=/var/lib/hermes-opencode-mcp
HERMES_MCP_SERVER_NAME=hermes-opencode-mcp
HERMES_MCP_SERVER_VERSION=0.1.0
HERMES_MCP_LOG_LEVEL=INFO
HERMES_MCP_LOG_JSON=1
```

Notes:
- `PYTHONPATH` should point to the repo `src` directory
- `HERMES_MCP_REPO_ROOT` should point to the repo root
- `HERMES_MCP_STATE_DIR` must be writable
- use `HERMES_MCP_EXECUTOR=mock` only for local testing

Verify the env file exists:

```bash
sudo test -f /etc/hermes-opencode-mcp/hermes-opencode-mcp.env && echo ok
```

---

## 7. Manual run for first validation

Do this before systemd.

```bash
source .venv/bin/activate
set -a
source /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
set +a
python -m hermes_opencode_mcp
```

Expected:
- process starts
- no immediate config crash
- it waits for stdio MCP input

If it exits immediately, read the error and fix env/targets first.

Stop with `Ctrl+C`.

---

## 8. Verify with tests

From the repo root:

```bash
source .venv/bin/activate
pytest -q
```

Expected: test suite passes.

---

## 9. Optional live E2E verification

Use this only when the target is real and OpenCode is ready.

```bash
source .venv/bin/activate
set -a
source /etc/hermes-opencode-mcp/hermes-opencode-mcp.env
set +a
python scripts/e2e_live.py \
  --target-id coding-node-1 \
  --directory /path/to/repo/on/target \
  --targets-file /etc/hermes-opencode-mcp/targets.json
```

Expected:
- JSON output containing `health`
- a terminal task result
- summary beginning with:

```text
oc@vm_name@ip_address:
```

If live E2E fails, do not continue to Telegram/Hermes integration yet.

---

## 10. Install as a systemd service

Copy the unit:

```bash
sudo cp deploy/systemd/hermes-opencode-mcp.service /etc/systemd/system/
```

Important:
- the provided unit uses:
  - `User=hermes`
  - `Group=hermes`
  - `WorkingDirectory=/opt/hermes-opencode-mcp`
- change those if your machine uses different paths/users

If deploying from the current checkout instead of `/opt/hermes-opencode-mcp`, edit the unit first:

```bash
sudoedit /etc/systemd/system/hermes-opencode-mcp.service
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-opencode-mcp
```

Check status:

```bash
sudo systemctl status hermes-opencode-mcp --no-pager
```

Check logs:

```bash
sudo journalctl -u hermes-opencode-mcp -f
```

Expected:
- service is active
- logs are flowing
- no repeated restart loop

---

## 11. Post-install validation checklist

Confirm all of the following:

- [ ] `opencode` exists on PATH
- [ ] targets file is valid JSON
- [ ] env file paths are correct
- [ ] state dir is writable
- [ ] `pytest -q` passes
- [ ] manual server run works
- [ ] systemd service starts cleanly
- [ ] optional live E2E passes

Only after this should you integrate Hermes and Telegram.

---

## 12. Hermes integration note

This repo is a stdio MCP server.

Hermes should launch it with something equivalent to:

```bash
python -m hermes_opencode_mcp
```

with the same environment variables from the env file.

Do not put Telegram-specific logic into this repo.

---

## 13. Commit changes

After making changes:

```bash
git status --short --branch
git add -A
git commit -m "Describe the change clearly"
```

Example:

```bash
git commit -m "Add install and release instructions"
```

Verify commit:

```bash
git show --stat --oneline --summary HEAD
```

---

## 14. Merge changes

If working on a feature branch:

```bash
git checkout main
git pull origin main
git merge <feature-branch>
```

If already on `main`, no merge step is needed.

Verify branch state:

```bash
git status --short --branch
```

---

## 15. Push changes

```bash
git push origin main
```

If push fails because of auth, fix credentials and retry.

Common checks:

```bash
git remote -v
git branch --all --verbose --no-abbrev
```

---

## 16. Quick operator summary

If an AI agent must do the minimum safe sequence, use this order:

1. clone repo
2. create venv
3. install with `pip install -e '.[dev]'`
4. confirm `opencode` exists
5. create `/etc/hermes-opencode-mcp/targets.json`
6. create `/etc/hermes-opencode-mcp/hermes-opencode-mcp.env`
7. manual run test
8. run `pytest -q`
9. optional `scripts/e2e_live.py`
10. install/start systemd service
11. commit
12. merge if needed
13. push

---

## 17. Known gotchas

- Missing `opencode` on PATH will break startup in `opencode` mode
- wrong `PYTHONPATH` will prevent import/runtime startup
- wrong `repo_path` in targets will break real execution
- wrong systemd `WorkingDirectory` or `User` will cause service failure
- `mock` mode is not production execution
- if persisted tasks exist across restart, startup reconciliation will mark queued/running tasks as failed by design
