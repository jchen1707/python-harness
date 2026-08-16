---
name: verify
description: Run the Definition of Done gates and report the actual output as evidence. Use before claiming work is complete, before opening a PR, or whenever asked whether the change actually works.
---

Prove the change works. **Paste real command output — never assert success.**

The same gates run automatically in the `Stop` hook
(`.agents/hooks/verify.py`), but only when Python under `src/` or `tests/`
changed. Invoke this skill when you want the evidence in the transcript, or to
cover the cases the hook deliberately skips.

## Gates

Run in order and **stop at the first failure** — a later gate's output is
meaningless once an earlier one fails.

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

With `--integration` in `$ARGUMENTS`, also run the DB-backed suite. It needs
Docker and the app extra:

```sh
uv sync --extra app
docker compose up -d db
uv run pytest -m integration
```

## Reporting

For each gate, report the command, its exit status, and the tail of its output.
Then one of:

- **PASS** — every gate green. State which gates ran and which were skipped.
- **FAIL** — name the first failing gate, quote the failure, and state the root
  cause if you can see it. Do not attempt the fix inside this skill; report and
  let the caller decide.

Two failure modes to call out explicitly rather than glossing:

- **No tests exist for the changed behaviour.** A green `pytest` proves nothing
  then. Say so — "4 passed, none covering the new code path" is the honest line.
- **A gate could not run** (missing Docker, no `src/app/main.py`, app extra not
  installed). That is not a pass. Report it as skipped, with the reason.

## When the app is runnable

Once `src/app/main.py` exists, a green test suite is still not proof the service
starts. Add a smoke check:

```sh
uv run uvicorn app.main:app --port 8001 &
curl -fsS http://127.0.0.1:8001/health
```

Kill the server afterwards. If there is no health route yet, say that instead of
inventing one.
