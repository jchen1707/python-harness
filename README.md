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
- `docs/agents/` — how agents work with this repo: `issue-tracker.md` (Linear conventions),
  `triage-labels.md` (canonical triage roles → real label strings), `domain.md`.
- `.out-of-scope/` — rejected feature requests, read by `/triage` to avoid re-litigating a
  decision that was already made.
- `.github/workflows/ci.yml` — CI gates (ruff, format, mypy, pytest; not the integration
  suite, which needs Docker).
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

## The SDLC

How a request travels from landing in the tracker to meeting the Definition of Done.
`CLAUDE.md` is the authority; this is the map.

```
   Linear issue
        │
        ▼
   /triage ─┬─▶ needs-triage ⇄ needs-info      evaluation loop, not terminal
            │
            ├─▶ ready-for-human · wontfix      leaves the pipeline
            │
            └─▶ ready-for-agent
                     │
                     ▼
   ┌── ALIGNMENT — one unbroken context ──────────────┐
   │  /grill-with-docs → /to-spec → /to-tickets       │
   └──────────────────────────────────────────────────┘
                     │ one ticket at a time
                     ▼
   ┌── EXECUTION — branch first, fresh context each ──┐
   │  /implement → /verify → /code-review             │
   └──────────────────────────────────────────────────┘
                     │
                     ▼
              PR → Definition of Done
```

### 1. Triage — decide if it's real and whose it is

A raw report lands in Linear. `/triage` gathers context first — exploring the codebase,
checking whether the thing is already implemented, reading `.out-of-scope/` for a prior
rejection — then **recommends a category and state with reasoning, and waits** for your
call. It never labels blind. Only once you've directed it does it verify the claim,
reproducing the bug (or checking out and running a PR) before writing any agent brief.

Exit: exactly one category label (`Bug` / `Feature`) and one state label.
`ready-for-agent`, with an agent brief attached, sends it down the pipeline.
`ready-for-human` and `wontfix` leave the pipeline. Neither `needs-triage` nor
`needs-info` is terminal — the first means evaluation is still in progress, and the second
returns to it once the reporter replies. Roles map to real label strings in
`docs/agents/triage-labels.md`.

### 2. Alignment — turn a request into tickets

**Keep these three steps in one unbroken context window — no `/compact`, no `/clear`.**
Each builds on the thinking of the last, and that continuity is the whole point.

| Step | Produces |
| --- | --- |
| `/grill-with-docs` | assumptions stress-tested against real docs, not model priors |
| `/to-spec` | a spec — behaviour and acceptance criteria, not implementation |
| `/to-tickets` | the spec split into independently implementable tickets |

Pick the architectural style here, during research — not while coding — and record it in
`docs/architecture.md`.

### 3. Execution — one ticket, one clean slate

**Start each `/implement` in a fresh context, working only from its ticket.** Alignment
needs continuity; execution needs a clean slate. Branch as `<type>/<TEAM-NUM>-<slug>`
(e.g. `feat/ENG-412-vector-store`) so `/code-review` can resolve the originating ticket
mechanically.

While you work, the hooks enforce themselves regardless of instructions: `protect_paths`
blocks edits to `.env`, `migrations/`, `generated/` and `uv.lock`; `format_edited` runs
ruff on every edited `.py`; `verify` blocks the turn while the gates fail — but **only**
when the turn changed Python under the gated paths, so prose work ends freely. That Stop
gate is what makes a session walk-away-able.

### 4. Verification and review

`/verify` runs the four fast gates and prints their output as evidence; pass
`--integration` to add the DB-backed suite, which needs Docker and `uv sync --extra app`.
`/code-review` then reads the diff on two independent axes — **Standards** (against
`docs/architecture.md` plus the summary in `CLAUDE.md`) and **Spec** (against the
originating ticket). Reviewers get read-only tools by design: one
that can edit will fix things instead of reporting them, and the independent signal is the
point.

### 5. Done

Commit, push the branch, open the PR. A feature branch and PR need no permission;
committing to `main` does. Capture any friction with `/retro` so the next session starts
smarter.

### The small-work path

Anything you could describe in one sentence — or work you want planned by one model and
built by another — skips alignment entirely:

```
/plan  →  (new terminal)  →  /implement-from-plan
```

`/plan` writes `.claude/plans/plan.md` + `test-plan.md`, gets explicit sign-off, and stops.
`/implement-from-plan` feeds those to `/implement` with this repo's gates pinned. Both
paths converge on step 4.

### Definition of Done

- All five gates pass: `ruff check` · `ruff format --check` · `mypy` · `pytest` ·
  `pytest -m integration`
- New behaviour has a test that would fail if the behaviour regressed
- `/code-review` clean on Standards; clean on Spec when there's an originating ticket
- Config and secrets read only through `app.config.Settings`
- Friction worth remembering captured via `/retro`

## Commands
Repo-owned (`.claude/commands/` + `.claude/skills/`):

| Slash | Does |
| --- | --- |
| `/plan` | research + plan a feature, write `.claude/plans/plan.md` (terminal 1) |
| `/implement-from-plan` | feed the plan + test plan to `/implement` with the `uv` gates pinned (terminal 2) |
| `/verify` | run the Definition of Done gates and print the output as evidence |
| `/loop-goal` | run a standing goal (docs, architecture, logging, tests, deps) until its stop condition holds |
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
| `/triage` | move tracker issues through the triage state machine (see `docs/agents/triage-labels.md`) |
| `/wait-what` | re-pitch a message that didn't land, in plain English |
| `/writing-for-agents` | write docs and prompts that agents actually follow |

Install (already declared in `.claude/settings.json`, so a clone needs only this once):
```sh
claude plugin marketplace add mattpocock/skills
claude plugin install mattpocock-skills@mattpocock --scope project
```
Upstream's own marketplace is used rather than Anthropic's official mirror, which lags.

`/writing-great-skills` was **renamed** to `/writing-for-agents` upstream (breaking, no
alias) and broadened to cover any agent-read document. Use the new name.

## Agentic setup

| Path | What |
| --- | --- |
| `.claude/agents/` | Subagents: `explorer`, `spec-checker`, `security-reviewer`, `test-writer` (worktree-isolated) |
| `.claude/hooks/` | `protect_paths` (block protected edits), `format_edited` (auto-format), `verify` (Stop gate on the Definition of Done) |
| `.claude/workflows/` | `full-review.js` — six reviewers fanned out, one ranked report fanned in |
Issues live in **Linear** via the claude.ai account connector — check `/mcp` for
*claude.ai Linear*, and note MCP tools only load at session start
(`docs/agents/issue-tracker.md`). PRs stay on GitHub.

## Notes
- On Windows/PowerShell, use `uv run` for everything; no `cd` prefix.
- The approved stack is fixed in `pyproject.toml` (`app` extra) — introducing a different
  framework requires updating `CLAUDE.md` + `docs/architecture.md` first.