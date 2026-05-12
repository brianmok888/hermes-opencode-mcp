# uv test pass and git hygiene notes

Use these notes when finishing a freshly scaffolded MCP-port repo.

## Preferred real test pass

If ad-hoc runtime checks were used first, finish with a real editable install and pytest run once `uv` is available:

```bash
uv venv --clear
. .venv/bin/activate
uv pip install -e .[dev]
pytest -q
```

Observed good result in this class of repo:
- editable install succeeds
- pytest runs cleanly
- example outcome: `11 passed`

## Git hygiene before first commit

Validation often leaves temp directories behind (for example `.tmp-check`, `.tmp-client`, `.tmp-config`).

Before the first commit:
1. add temp patterns to `.gitignore`
2. remove temp dirs from the working tree
3. if already staged, unstage them with `git rm --cached -r ...`
4. re-check `git status --short`

Useful ignore additions for this class of repo:

```gitignore
.tmp-*/
uv.lock
```

## Commit pitfall

A clean repo can still fail to commit if git identity is unset. If `git commit` fails with author identity unknown, set repo-local or global `user.name` / `user.email` before retrying.
