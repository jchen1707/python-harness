# Loop goals — this repo

<!-- harness:agnostic -->

**Shared doctrine lives in `.agents/vendor/harness/skills/loop-goal/SKILL.md`** — the
protocol, the guardrails, the four goals that hold anywhere. It is vendored from
[`harness`](https://github.com/jchen1707/harness) and pinned by sha; read it first.

<!-- /harness:agnostic -->
<!-- harness:claude
**Shared doctrine is provided by the `harness` plugin**, as the `loop-goal` skill — the
protocol, the guardrails, the four goals that hold anywhere. Read it first.
/harness:claude -->

This file records only what is true in **this** repo.

## The four shared goals, sharpened

| Goal           | Stop condition here                                                                                                                                                                       |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs`         | Every claim in `AGENTS.md`, `README.md`, `docs/architecture.md` and every `src/app/*/AGENTS.md` matches the code; every documented command runs; no reference to a deleted file or command |
| `architecture` | No layering violation (`api` → `services` → `ai` → `repositories` → `config`, no reverse deps); every cross-layer dependency goes through a protocol in `repositories/`; the gates green   |
| `tests`        | Every public function in `src/app/` has at least one test exercising a real behaviour; every failure mode from the test plan is covered; `uv run pytest` green                             |
| `deps`         | Every dependency in `pyproject.toml` is used; nothing used is missing; the approved-stack list in `AGENTS.md` matches what is installed                                                    |

## Goals only this repo has

| Goal      | Stop condition                                                                                                                                                 |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `logging` | Every error path and every external call (DB, LLM, embeddings, HTTP) emits a structlog event with bound context; no bare `except: pass`; no `print()`          |
| `async`   | No blocking call on the event loop; no `async def` that never awaits; every blocking I/O call wrapped in `asyncio.to_thread`; no unbounded concurrency          |

## The gate that stops looking

`mypy` reads only the paths in `pyproject.toml`'s `files`. A goal whose stop condition is "the
gates are green" terminates the moment the work moves into a directory `files` does not name —
green, and checking nothing. That is a finding about the gate, not a completed loop.
