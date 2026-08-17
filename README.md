# python-harness

Guardrails, workflow, and standards for Python development — **a harness, not an
application.** It defines how to develop Python here (workflow, linting, architectural
standards, context/memory management) and leaves the application code for you to write
per those standards.

Target workload: backend web development, RAG applications, and AI agent orchestration
(FastAPI · Pydantic v2 · LangGraph + langchain-anthropic · Voyage embeddings ·
Postgres + pgvector).

## What's here
- `AGENTS.md` — the source of truth for every coding harness. Each `CLAUDE.md` is a thin
  compatibility pointer to the adjacent `AGENTS.md`.
- `docs/architecture.md` — **cross-cutting** standards only: layering, protocols, types,
  scaling, extensibility, concurrency, containers, dependency policy (load with `/arch`).
- `pyproject.toml` — tool config (ruff, mypy, pytest) + the approved app stack as the
  opt-in `app` extra (no runtime deps by default).
- `.agents/` — portable skills, agent prompts, and workflows. This is the canonical
  capability directory.
- `.claude/` — the Claude Code adapter: settings, hooks, slash commands, and symlinks to
  the canonical `.agents/` capability directories.
- `.codex/` — the Codex adapter: unattended execution settings, custom agent adapters,
  and the shared Stop verification hook.
- `docs/agents/` — how agents work with this repo: `issue-tracker.md` (Linear conventions),
  `triage-labels.md` (canonical triage roles → real label strings), `domain.md`.
- `.out-of-scope/` — rejected feature requests, read by `/triage` to avoid re-litigating a
  decision that was already made.
- `.github/workflows/ci.yml` — CI gates (ruff, format, mypy, pytest; not the integration
  suite, which needs Docker).
- `.pre-commit-config.yaml` — pre-commit hooks (ruff + mypy + hygiene).
- `docker-compose.yml` — dev infra: Postgres + pgvector (`docker compose up -d db`).
- `src/app/` — package scaffold, no application code yet. Each directory carries its own
  `AGENTS.md` with the conventions that govern it (see below).

## Layout — rules live next to the code

Each directory owns its conventions. Harnesses that support `AGENTS.md` load these files
by scope. Other harnesses must follow the adjacent compatibility pointer.

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
`repositories/AGENTS.md`. That is why anything spanning layers stays in
`docs/architecture.md` — a cross-layer rule in a leaf file stops being enforced exactly
where it matters. Root `AGENTS.md` indexes both, and carries a reference table mapping a
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

### Symbol navigation

Codex starts `pyright-lsp` through `.codex/start-pyright-mcp.sh`. The script installs
pinned tools in the sandbox cache when required. A new template project needs no manual
installation.

MCP servers load at session start. Confirm the connection with `/mcp`. See `AGENTS.md` →
Symbol navigation for usage rules.

## The SDLC

How a request travels from landing in the tracker to meeting the Definition of Done.
`AGENTS.md` is the authority; this is the map.

```
   Linear issue
        │
        ▼
   /triage ◆ ─┬─▶ needs-triage ⇄ needs-info    evaluation loop, not terminal
              ├─▶ ready-for-human · wontfix    leaves the pipeline
              └─▶ ready-for-agent
                       │
                       ▼
   ┌── ALIGNMENT — one unbroken context ────────────────────┐
   │  /grill-with-docs ◆ → /to-spec ◆ → /to-tickets ◆       │
   └────────────────────────────────────────────────────────┘
                       │ one ticket at a time
                       ▼
   ┌── EXECUTION — branch first, fresh context per ticket ──┐
   │  ( /plan ◆ only if the ticket needs it ) → /implement  │
   │                        → /verify → /code-review        │
   └────────────────────────────────────────────────────────┘
                       │
                       ▼
                PR → Definition of Done

   ◆ = stops and waits for you. Nothing past a ◆ happens without your say-so.
```

### Where you're in the loop

Four checkpoints before a line of code is written, and none of them are advisory — each
iterates until you approve.

| Checkpoint | What you're approving | What happens if you say no |
| --- | --- | --- |
| `/triage` | the category and state call, with reasoning | it re-evaluates; it never labels blind |
| `/grill-with-docs` | your own assumptions, round by round | keeps grilling; ADRs and glossary entries land as you settle things |
| `/to-spec` | **the seams** — where tests will attach | re-sketches before writing the spec |
| `/to-tickets` | the breakdown: granularity, blocking edges | re-slices, and iterates until you're happy |
| `/plan` *(optional)* | per-ticket approach + test plan | revises and re-asks; it will not proceed to code |

After that the loop changes shape: `/verify` and `/code-review` **report to you** rather
than asking permission — they surface evidence and findings, and reviewers are read-only by
design so they can't quietly act on what they find. The hooks are the one thing that never
asks: they run in the harness and hold regardless of what any instruction says.

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

| Step | Produces | You are asked to |
| --- | --- | --- |
| `/grill-with-docs` | assumptions stress-tested against real docs, not model priors; ADRs and glossary entries as decisions land | answer rounds of questions — this is an interview, not a report |
| `/to-spec` | the spec: problem, user stories, **Implementation Decisions**, **Testing Decisions**, out-of-scope | **confirm the seams** before the spec is written |
| `/to-tickets` | the spec split into tracer-bullet tickets with blocking edges | approve the breakdown — granularity and blocking edges, iterating until you're happy |

**Alignment plans the how, not just the what.** The spec's *Implementation Decisions*
section covers the modules to be built or changed, their interfaces, architectural
decisions, schema changes and API contracts; *Testing Decisions* records which modules get
tested and the prior art to follow. Both are published to the tracker, so the implementer
reads a design, not just a wish.

The seam check in `/to-spec` matters more than it looks. `/tdd` refuses to write a test at
an unconfirmed seam — *"No test is written at an unconfirmed seam"* — and this is where
that confirmation is obtained, once, for the whole feature.

Pick the architectural style here, during research — not while coding — and record it in
`docs/architecture.md`.

#### Where the Matt Pocock skills fit

These skills add optional steps to the main path. Do not run all three for every ticket.

| Skill | Place it | Use it when |
| --- | --- | --- |
| `/improve-codebase-architecture` | During alignment, after `/grill-with-docs` and before `/to-spec` | The change exposes architectural friction, shallow modules, or hard-to-test code. It scans the codebase and gives you candidates to choose from. |
| `/codebase-design` | During alignment, after you choose a candidate and before `/to-spec` confirms the seams | The module, interface, or seam needs design. Use its deep-module vocabulary to reduce the interface and hide more behavior behind it. |
| `/tdd` | During execution, inside `/implement`, after `/to-spec` or `/plan` confirms the seams | The ticket adds or changes behavior. Run one red → green cycle per vertical slice, then refactor during review. |

For architecture work, use this order:

```
/grill-with-docs → /improve-codebase-architecture → /codebase-design
→ /to-spec → /to-tickets → /implement → /tdd → /verify → /code-review
```

Skip the two architecture skills when the design is already clear. For the small-work path,
run `/tdd` inside `/implement-from-plan` after plan sign-off. Skip `/tdd` for documentation-only
or configuration-only changes.

### 3. Execution — one ticket, one clean slate

**Start each ticket in a fresh context, working only from that ticket.** Alignment needs
continuity; execution needs a clean slate. Branch as `<type>/<TEAM-NUM>-<slug>`
(e.g. `feat/BAC-412-vector-store`) so `/code-review` can resolve the originating ticket
mechanically.

The design already exists: it's in the spec's *Implementation Decisions*, agreed with you in
step 2. `/implement` works from the ticket and that spec — it does not need to invent an
approach, and shouldn't.

**When to add `/plan` on top.** `/implement` is deliberately thin — implement the spec, use
`/tdd` at pre-agreed seams, typecheck, review, commit — with no design step of its own. That
is fine when the spec's decisions reach far enough into the ticket. Add `/plan` when they
don't:

- The ticket is large, or its approach is genuinely ambiguous after reading the spec.
- The spec's decisions were written for the feature and don't say much about *this* slice.
- You want the design settled by one model and built by another — `/plan` and
  `/implement-from-plan` are a clean handoff seam.
- The implementing terminal can't reach the tracker, so the spec needs pinning to local
  files it can read.

`/plan` researches the ticket, settles layer placement and the sync/async boundary, and
writes `.agents/plans/plan.md` + `test-plan.md` for your explicit sign-off, then stops.
`/implement-from-plan` then feeds both to `/implement` as the spec, turns the numbered Steps
into the task list, and pins this repo's `uv` gates in place of the skills' generic
TypeScript phrasing.

For a routine ticket off a well-specified feature, this is ceremony you don't need — the
spec did the work already. Reach for it deliberately, not by default.

While you work, the hooks enforce themselves regardless of instructions: `protect_paths`
blocks edits to `.env`, `migrations/`, `generated/` and `uv.lock`; `format_edited` runs
ruff on every edited `.py`; `verify` blocks the turn while the gates fail — but **only**
when the turn changed Python under the gated paths, so prose work ends freely. That Stop
gate is what makes a session walk-away-able.

### 4. Verification and review

`/verify` runs the four fast gates and prints their output as evidence; pass
`--integration` to add the DB-backed suite, which needs Docker and `uv sync --extra app`.
`/code-review` then reads the diff on two independent axes — **Standards** (against
`docs/architecture.md` plus the summary in `AGENTS.md`) and **Spec** (against the
originating ticket). Reviewers get read-only tools by design: one
that can edit will fix things instead of reporting them, and the independent signal is the
point.

For a change that warrants more than two axes, `.agents/workflows/full-review.js` fans the
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

Here `/plan` is not optional — it's the **only** planning checkpoint, and the only place you
approve anything. With no spec to carry the Implementation Decisions and no seam check from
`/to-spec`, `plan.md` and `test-plan.md` do that job instead. That inverts step 3: on the
main path `/plan` is a deliberate addition; here it's the whole design step.

Both paths converge on step 4.

The new terminal is optional but useful: `/plan` and `/implement-from-plan` are a clean
model-switching seam, so you can plan with one model and build with another.

### Definition of Done

- All five gates pass: `ruff check` · `ruff format --check` · `mypy` · `pytest` ·
  `pytest -m integration`
- New behaviour has a test that would fail if the behaviour regressed
- `/code-review` clean on Standards; clean on Spec when there's an originating ticket
- Config and secrets read only through `app.config.Settings`
- Friction worth remembering captured via `/retro`

## Capabilities

Repo-owned skills live in `.agents/skills/`. Claude Code sees the same files through the
`.claude/skills` adapter. Claude-only slash-command wrappers live in `.claude/commands/`.

| Slash | Does |
| --- | --- |
| `/plan` | research + plan a feature, write `.agents/plans/plan.md` (terminal 1) |
| `/implement-from-plan` | feed the plan + test plan to `/implement` with the `uv` gates pinned (terminal 2) |
| `/verify` | run the Definition of Done gates and print the output as evidence |
| `/full-review` | fan one diff out to nine reviewers, then consolidate and rank their findings |
| `/loop-goal` | run a standing goal (docs, architecture, logging, tests, deps) until its stop condition holds |
| `/test` | `uv run pytest` |
| `/lint` | ruff check + format-check + mypy |
| `/run` | uvicorn dev server (needs `src/app/main.py`) |
| `/arch` | load `docs/architecture.md` into context |
| `/context` | context/memory hygiene audit |
| `/retro` | capture a lesson from a bug/tool-friction to memory so future sessions go smoother |
| `/prune-rules` | audit the rule files for drift, duplication and dead rules, then refine them |
| `/search-second-brain` | search past sessions' learnings and report the pattern across them |

The workflow also uses these optional upstream capabilities from `mattpocock/skills`:

| Slash | Does |
| --- | --- |
| `/implement` | implement from a spec or set of tickets, then commit (prefer `/implement-from-plan` here) |
| `/code-review` | two-axis review since a fixed point: Standards + Spec |
| `/tdd` | red-green-refactor loop |
| `/codebase-design` | design a deep module, its interface, and its seam |
| `/improve-codebase-architecture` | scan for shallow modules and propose deepening candidates |
| `/diagnosing-bugs` | diagnosis loop for hard bugs and perf regressions |
| `/research` | investigate a question against primary sources, write findings to a file |
| `/triage` | move tracker issues through the triage state machine (see `docs/agents/triage-labels.md`) |
| `/wait-what` | re-pitch a message that didn't land, in plain English |
| `/writing-for-agents` | write docs and prompts that agents actually follow |

Claude Code installs them as a plugin:
```sh
claude plugin marketplace add mattpocock/skills
claude plugin install mattpocock-skills@mattpocock --scope project
```
Upstream's own marketplace is used rather than Anthropic's official mirror, which lags.

Codex does not load Claude plugins. Install the upstream repository with Codex's
`skill-installer`, or install equivalent skills with the same capability names. If an
optional capability is absent, follow the workflow described in `AGENTS.md` directly.

`/writing-great-skills` was **renamed** to `/writing-for-agents` upstream (breaking, no
alias) and broadened to cover any agent-read document. Use the new name.

## Agentic setup

| Path | What |
| --- | --- |
| `.agents/agents/` | Subagents. Workers: `explorer`, `test-writer` (worktree-isolated). Reviewers, one per `full-review` axis and each invokable standalone: `standards-reviewer`, `spec-checker`, `security-reviewer`, `test-reviewer`, `async-reviewer`, `simplicity-reviewer`, `design-reviewer`, `perf-reviewer`, `cost-reviewer` |
| `.agents/skills/` | Harness-neutral repo skills. Claude Code loads them through `.claude/skills`. Other harnesses can load this directory directly or install it into their skill search path. |
| `.agents/hooks/` | `protect_paths` (block protected edits), `format_edited` (auto-format), `verify` (Stop gate on the Definition of Done), `session_learnings` (SessionEnd: distils lessons to the second brain), `vault_index` (rebuilds the vault's Markdown indexes) |
| `.agents/workflows/` | `full-review.js` — nine reviewers fanned out, one ranked report fanned in. Each axis reads its prompt from the matching `.agents/agents/` definition, so the two forms cannot drift |

Issues live in **Linear**. Workspace **Development**, default team **Backend** (`BAC`).
Claude uses the server in `.mcp.json`. Codex receives the host-authorized server through
`sbx --static-mcp linear`. MCP tools load at session start. PRs stay on GitHub.

Register Linear once with `sbx mcp add linear --url https://mcp.linear.app/mcp`. Start each
Codex sandbox with `--static-mcp linear`. The host registration then works for new sessions
and template-derived projects.

Lifecycle hooks are defense in depth. Claude Code and Codex enable protected paths,
formatting, verification, and session learning. Codex also blocks common secret reads.
CI and pre-commit enforce checks independently.

Codex uses the persistent equivalent of `codex --yolo`: `approval_policy = "never"` and
`sandbox_mode = "danger-full-access"`. It does not pause for command approvals. The Stop
hook still keeps the turn running when a gate fails. Review and trust it once with `/hooks`.

## Notes
- On Windows/PowerShell, use `uv run` for everything; no `cd` prefix.
- The approved stack is fixed in `pyproject.toml` (`app` extra) — introducing a different
  framework requires updating `AGENTS.md` + `docs/architecture.md` first.
