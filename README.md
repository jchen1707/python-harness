# python-harness

Guardrails, workflow, and standards for Python development — **a harness, not an
application.** It defines how to develop Python here (workflow, linting, architectural
standards, context/memory management) and leaves the application code for you to write
per those standards.

Target workload: backend web development, RAG applications, and AI agent orchestration
(FastAPI · Pydantic v2 · LangGraph + langchain-anthropic · Voyage embeddings ·
Postgres + pgvector).

## What's here
- `CLAUDE.md` — the source of truth: stack, workflow, Definition of Done, context/memory
  guidance, model guidance. Loaded every Claude Code session.
- `docs/architecture.md` — detailed architectural standards (load with `/arch`).
- `pyproject.toml` — tool config (ruff, mypy, pytest) + the approved app stack as the
  opt-in `app` extra (no runtime deps by default).
- `.claude/` — shared Claude Code config: `settings.json` (pre-approved safe commands)
  + `commands/` (`/plan`, `/test`, `/lint`, `/run`, `/arch`, `/context`, `/retro`).
- `.claude/settings.json` → `enabledPlugins` — declares the `mattpocock-skills` plugin
  (25 skills incl. `/implement`, `/code-review`, `/tdd`), so a clone picks it up
  automatically and it self-updates. `.claude/skills/` holds repo-owned skills only.
- `.github/workflows/ci.yml` — CI gates (ruff, mypy, pytest).
- `.pre-commit-config.yaml` — pre-commit hooks (ruff + mypy + hygiene).
- `docker-compose.yml` — dev infra: Postgres + pgvector (`docker compose up -d db`).
- `src/app/` — empty package scaffold (the standard layout; populate per
  `docs/architecture.md`).

## Setup
Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).
```sh
# Install uv if needed:
#   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Sync the harness tooling:
uv sync
# When you start writing app code, install the approved stack:
uv sync --extra app
# (Optional) set up pre-commit hooks:
uv run pre-commit install
# (Optional) start the dev vector DB:
docker compose up -d db
```
Copy `.env.example` → `.env` and fill in keys (never commit `.env`).

## Workflow
See `CLAUDE.md` → "Development workflow" + "Definition of Done". In short: implement in
the right layer → `uv run ruff check .` → `uv run ruff format --check .` → `uv run mypy`
→ `uv run pytest` → `/code-review` against standards → commit.

## Commands
Repo-owned (`.claude/commands/`):

| Slash | Does |
| --- | --- |
| `/plan` | research + plan a feature, write `.claude/plans/plan.md` (terminal 1) |
| `/implement-from-plan` | feed the plan + test plan to `/implement` with the `uv` gates pinned (terminal 2) |
| `/test` | `uv run pytest` |
| `/lint` | ruff check + format-check + mypy |
| `/run` | uvicorn dev server (needs `src/app/main.py`) |
| `/arch` | load `docs/architecture.md` into context |
| `/context` | context/memory hygiene audit |
| `/retro` | capture a lesson from a bug/tool-friction to memory so future sessions go smoother |

From the `mattpocock-skills` plugin (v1.2.1, 25 skills — highlights):

| Slash | Does |
| --- | --- |
| `/implement` | implement from a spec or set of tickets, then commit (prefer `/implement-from-plan` here) |
| `/code-review` | two-axis review since a fixed point: Standards + Spec |
| `/tdd` | red-green-refactor loop |
| `/diagnosing-bugs` | diagnosis loop for hard bugs and perf regressions |
| `/research` | investigate a question against primary sources, write findings to a file |
| `/wait-what` | re-pitch a message that didn't land, in plain English |
| `/writing-for-agents` | write docs and prompts that agents actually follow |

Install (already declared in `.claude/settings.json`, so a clone needs only this once):
```sh
claude plugin marketplace add mattpocock/skills
claude plugin install mattpocock-skills@mattpocock --scope project
```
Upstream's own marketplace is used rather than Anthropic's official mirror, which lags.

Repo-owned skill in `.claude/skills/`: `writing-great-skills` — kept because upstream
deleted it, so nothing will ever update it.

## Notes
- On Windows/PowerShell, use `uv run` for everything; no `cd` prefix.
- The approved stack is fixed in `pyproject.toml` (`app` extra) — introducing a different
  framework requires updating `CLAUDE.md` + `docs/architecture.md` first.