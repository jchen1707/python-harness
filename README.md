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
- `docs/architecture.md` — **cross-cutting** standards only: layering, protocols, types,
  scaling, extensibility, concurrency, containers, dependency policy (load with `/arch`).
- `pyproject.toml` — tool config (ruff, mypy, pytest) + the approved app stack as the
  opt-in `app` extra (no runtime deps by default).
- `.claude/` — shared Claude Code config: `settings.json` (pre-approved safe commands),
  `commands/` and `skills/` (both tabled under [Commands](#commands) below).
- `.claude/settings.json` → `enabledPlugins` — declares the `mattpocock-skills` plugin, so
  a clone picks it up automatically and it self-updates. `.claude/skills/` holds
  repo-owned skills only.
- `docs/agents/` — how agents work with this repo: `issue-tracker.md` (Linear conventions),
  `triage-labels.md` (canonical triage roles → real label strings), `domain.md`.
- `.out-of-scope/` — rejected feature requests, read by `/triage` to avoid re-litigating a
  decision that was already made.
- `.github/workflows/ci.yml` — CI gates (ruff, format, mypy, pytest; not the integration
  suite, which needs Docker).
- `.pre-commit-config.yaml` — pre-commit hooks (ruff + mypy + hygiene).
- `docker-compose.yml` — dev infra: Postgres + pgvector (`docker compose up -d db`).
- `src/app/` — package scaffold, no application code yet. Each directory carries its own
  `CLAUDE.md` with the conventions that govern it (see below).

## Layout — rules live next to the code

Each directory owns its conventions. Read the file for the directory you are changing;
Claude Code loads it automatically when working there.

```
src/app/
├── api/            HTTP edge — status codes, pagination, Annotated deps
├── services/       orchestration, transaction boundaries, bounded fan-out
├── ai/             applied AI — why it is its own layer
│   ├── retrieval/  chunking, embedding, hybrid search, filtering
│   ├── reranking/  cross-encoders, fusion, diversity, fallback order
│   ├── agents/     LangGraph, prompt caching, tools, token budgets
│   └── evals/      datasets, metric per layer, when to run
├── repositories/   SQL, pgvector indexes, protocols, connection pools
└── core/           Settings, structlog, Prometheus metrics, errors, retries
tests/              unit vs integration, seams, fakes, determinism
```

Dependency direction, one way:

```
api  ──▶  services  ──▶  ai  ──▶  repositories  ──▶  config
```

`core/` is cross-cutting — every layer may import it, it imports none of them.
`ai/evals/` is the one documented exception: it may import any layer, and nothing
imports it, which is safe only because it never runs in a request.

**These files are path-scoped.** Working in `api/` does not load
`repositories/CLAUDE.md`. That is why anything spanning layers stays in
`docs/architecture.md` — a cross-layer rule in a leaf file stops being enforced exactly
where it matters. Root `CLAUDE.md` indexes both, and carries a reference table mapping a
task to the file to read before starting it.

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

### Symbol navigation (optional, once per machine)

`.mcp.json` declares a `pyright-lsp` server so agents can resolve Python **symbols**
instead of grepping for text. Both binaries must be on `PATH`:

```sh
npm install -g pyright
go install github.com/isaacphi/mcp-language-server@latest   # then add GOPATH/bin to PATH
```

MCP servers load at session start, so a fresh install needs a restart. Confirm with
`/mcp`. When to prefer it over grep: `CLAUDE.md` → Symbol navigation.

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
   ┌── EXECUTION — branch first, fresh context per ticket ─┐
   │  /plan → sign-off → /implement-from-plan              │
   │                       → /verify → /code-review        │
   └───────────────────────────────────────────────────────┘
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

Alignment does settle design, but at **spec** level. `/to-spec` records **Implementation
Decisions** (modules, interfaces, schema changes, API contracts) and **Testing Decisions**,
and its step 2 confirms the test seams with you before writing anything.

Those decisions then stop at the ticket boundary on purpose: `/to-tickets` states each
ticket as *"end-to-end behaviour, from the user's perspective — not a layer-by-layer
implementation list."* Combine that with the fresh-context rule in step 3 and an
implementing agent starts from a ticket that deliberately withholds the spec's design.
That gap is real, and step 3 is where it gets closed — per ticket.

### 3. Execution — one ticket, one clean slate

**Start each ticket in a fresh context, working only from that ticket.** Alignment needs
continuity; execution needs a clean slate. Branch as `<type>/<TEAM-NUM>-<slug>`
(e.g. `feat/BAC-412-vector-store`) so `/code-review` can resolve the originating ticket
mechanically.

**Then plan the ticket before building it — `/plan` first, not `/implement` first.**

`/implement` is deliberately thin: implement the spec, use `/tdd` at pre-agreed seams,
typecheck, review, commit. It contains no design step. Handing it a ticket directly means
the approach — layer placement, which protocols to extend, the sync/async boundary — gets
decided while typing, which is exactly what `docs/architecture.md` says not to do.

`/plan` fills that gap per ticket. It researches the ticket, settles the design, and writes
`.claude/plans/plan.md` + `test-plan.md` for your explicit sign-off, then stops.

The test plan carries the seam confirmation across the context boundary. `/tdd` will not
write a test at an unconfirmed seam — *"No test is written at an unconfirmed seam"* — and
a fresh `/implement` context cannot see that `/to-spec` already confirmed them with you.
`test-plan.md` is what re-supplies that confirmation. On the small-work path below, where
no spec ran at all, it is the **only** thing that supplies it.

Then `/implement-from-plan` takes over: it feeds both plans to `/implement` as the spec,
turns the numbered Steps into the task list, hands the test cases over as the pre-agreed
seams, and pins this repo's `uv` gates in place of the skills' generic TypeScript phrasing.

This is why both paths share an ending — the small-work path below is the same two steps
without alignment in front of them.

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

For a change that warrants more than two axes, `.claude/workflows/full-review.js` fans the
same diff out to **nine** independent reviewers — standards, spec, security, tests,
async, simplicity, design, speed, cost — then fans in to a single synthesiser that merges
duplicates, drops
anything ruff or mypy already enforces, and ranks by severity and by how many axes agreed
independently. The synthesiser never reads the diff itself; it only reconciles what came
back, because a reviewer that also ranks tends to rank its own findings first.

Run it with `/workflows`, or trigger workflow mode with the `ultracode` keyword. It reviews
against `main` unless `REVIEW_BASE` says otherwise (`$env:REVIEW_BASE = "..."` in
PowerShell).

Reach for `/code-review` by default and `full-review` when the diff touches security,
concurrency, or anything you would not want to be wrong about.

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

This is step 3 with nothing in front of it. Same two commands, same sign-off, same gates —
the only difference is that no grilling, spec or tickets preceded them, because the work
was small enough not to need them. Both paths converge on step 4.

The new terminal is optional but useful: `/plan` and `/implement-from-plan` are a clean
model-switching seam, so you can plan with one model and build with another.

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
| `/prune-rules` | audit the rule files for drift, duplication and dead rules, then refine them |
| `/search-second-brain` | search past sessions' learnings and report the pattern across them |

From the `mattpocock-skills` plugin — highlights only; the plugin self-updates, so run
`/help` for the list it actually ships today:

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
| `.claude/agents/` | Subagents. Workers: `explorer`, `test-writer` (worktree-isolated). Reviewers, one per `full-review` axis and each invokable standalone: `standards-reviewer`, `spec-checker`, `security-reviewer`, `test-reviewer`, `async-reviewer`, `simplicity-reviewer`, `design-reviewer`, `perf-reviewer`, `cost-reviewer` |
| `.claude/hooks/` | `protect_paths` (block protected edits), `format_edited` (auto-format), `verify` (Stop gate on the Definition of Done), `session_learnings` (SessionEnd: distils lessons to the second brain), `vault_index` (rebuilds the vault's Markdown indexes) |
| `.claude/workflows/` | `full-review.js` — nine reviewers fanned out, one ranked report fanned in. Each axis reads its prompt from the matching `.claude/agents/` definition, so the two forms cannot drift |

Issues live in **Linear**, declared as a project MCP server in `.mcp.json` and pre-approved
in `.claude/settings.json`. Workspace **Development**, default team **Backend** (`BAC`).
Set `LINEAR_API_KEY` in your *user* settings — `.mcp.json` is committed and holds only the
`${LINEAR_API_KEY}` reference. MCP tools load at session start
(`docs/agents/issue-tracker.md`). PRs stay on GitHub.

## Notes
- On Windows/PowerShell, use `uv run` for everything; no `cd` prefix.
- The approved stack is fixed in `pyproject.toml` (`app` extra) — introducing a different
  framework requires updating `CLAUDE.md` + `docs/architecture.md` first.