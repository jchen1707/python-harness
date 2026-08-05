# python-harness

A **harness, not an application**: it defines *how* to build here. Application code goes in
`src/app/` per `docs/architecture.md`. Workload: backend web, RAG, agent orchestration.

## Commands

Everything runs through `uv`. Gates, in the order `/verify` runs them:

```sh
uv run ruff check .        # lint
uv run ruff format --check .
uv run mypy                # disallow_untyped_defs
uv run pytest              # unit only; offline
uv run pytest -m integration   # needs Docker + `uv sync --extra app`
```

`uv sync` installs tooling; `uv sync --extra app` adds the application stack (opt-in, so
the harness stays dependency-free until you build something).

## The workflow

**Ticket-shaped work** runs the main flow, in one unbroken context through `/to-tickets`:

```
/grill-with-docs  →  /to-spec  →  /to-tickets  →  /implement  →  /code-review
```

Alignment work needs continuity; execution work needs a clean slate. Keep steps 1–3 in one
context window — no `/compact`, no `/clear` — so the grilling, spec and tickets build on the
same thinking. Then start each `/implement` **fresh**, working only from its ticket.

**Small work** — anything you could describe in one sentence, or a change you want planned
by one model and built by another — uses the repo's own path instead:

```
/plan  →  (new terminal)  →  /implement-from-plan
```

`/plan` writes `.claude/plans/plan.md` + `test-plan.md`, gets explicit sign-off, and stops.
`/implement-from-plan` feeds those files to `/implement` with this repo's gates pinned.
Choose this when the work is too small to spec, or when you want the model-switching handoff.

Either path ends the same way: `/verify`, then `/code-review`, then commit. Committing to a
feature branch and opening a PR needs no permission; committing to `main` does.

### Definition of Done

- All five gate commands above pass
- New behaviour has a test that would fail if the behaviour regressed
- `/code-review` clean on Standards; clean on Spec when there's an originating ticket
- Config and secrets read only through `app.config.Settings`
- Friction worth remembering captured via `/retro`

## What is enforced automatically

Hooks run in the harness, so they hold regardless of what any instruction here says. See
`.claude/hooks/`:

| Hook | Effect |
| --- | --- |
| `protect_paths.py` (PreToolUse) | Blocks edits to `.env`, `migrations/`, `generated/`, `uv.lock` |
| `format_edited.py` (PostToolUse) | Runs `ruff format` + `ruff check --fix` on each edited `.py` |
| `verify.py` (Stop) | Blocks the turn while the gates fail — **only** when the turn changed `.py` under `src/`, `tests/` or `.claude/hooks/`, or changed `pyproject.toml` |

The Stop gate is what makes a session walk-away-able. `CLAUDE_SKIP_VERIFY=1` disables it.
The harness overrides a Stop hook after 8 consecutive blocks; if you hit that, the loop is
stuck on something it cannot fix.

The gated set is *code the gates check, plus the config that defines them* — so prose,
plans and docs still end freely and never burn override budget. Widen it by editing
`GATED_PATHS` / `GATED_FILES` in `verify.py`; `tests/test_verify_hook.py` pins the
pathspec, so dropping an entry fails the suite rather than silently going quiet.

## Parallel development

Worktrees are the unit of isolation — separate checkouts mean parallel agents cannot collide
on files. `.claude/agents/test-writer.md` sets `isolation: worktree`; add it to any subagent
that writes. Claude Code blocks a worktree agent from redirecting git back into the main
checkout, so the isolation actually holds.

Subagents in `.claude/agents/` — each defines its own tools and model:

| Agent | For |
| --- | --- |
| `explorer` | "Where is X handled?" — findings reach you, file contents don't |
| `spec-checker` | Diff vs. ticket; reports gaps only |
| `security-reviewer` | Fresh-context security pass |
| `test-writer` | Writes tests, never touches `src/` |

**Fork for breadth, stay inline for depth.** Scanning and summarising belong in a subagent;
reasoning you need to steer belongs in the main context. Reviewers get read-only tools by
design — one that can edit will fix things instead of reporting them, and the independent
signal is the whole point.

## Loops and workflows

- **`/loop-goal <goal>`** — standing goals that run until a stop condition holds (docs,
  architecture, logging, tests, deps). Progress lives in `.claude/plans/loop-<goal>.md` so it
  survives compaction.
- **`.claude/workflows/full-review.js`** — dynamic workflow fanning a diff out to six
  independent reviewers and fanning in to one ranked report. Run it with `/workflows`, or
  trigger workflow mode with the `ultracode` keyword.

## Standards

`docs/architecture.md` is authoritative — load it with `/arch` before non-trivial design work.
The rules that apply to every change:

- **Layering**: `api` → `services` → `repositories` → `config`. Dependencies point one way.
- **Depend on protocols**, not classes. `Embedder`, `VectorStore`, `Tool` live in
  `repositories/`; inject implementations.
- **Async for I/O, plain `def` for CPU and in-memory logic.** Async buys concurrency, not
  virtue. Offload blocking calls with `asyncio.to_thread`. The plan justifies the boundary.
- **Pydantic for every I/O surface** — requests, responses, tool inputs, config.
- **Log through structlog** with bound context; let exceptions surface with their cause.
- **Type every public function.**
- **Unit tests stay offline** (fakes and stubs); integration tests use testcontainers against
  ephemeral pgvector.

Pick the architectural style during research, not while coding, and record the choice in
`docs/architecture.md`.

## Stack

Fixed in `pyproject.toml` (`app` extra) — read it there. What the file doesn't explain:

- **Voyage AI** for embeddings because Anthropic has no embeddings API.
- **Postgres + pgvector** over a dedicated vector DB — one datastore, one backup story.
- **LangGraph** for agent orchestration in `services/agents/`.
- Introducing an alternative to any of these means updating `docs/architecture.md` first.

## Agent code in `services/agents/`

- Default `claude-opus-4-8`; `claude-sonnet-4-6` for high-volume routine work. Configure via
  `Settings.anthropic_model`, not inline strings.
- Adaptive thinking: `thinking: {type: "adaptive"}`. Passing `temperature`, `top_p`, `top_k`
  or `budget_tokens` returns 400 on Opus 4.8 / Fable 5.
- Cache static system prompts (`cache_control: ephemeral`, max 4 breakpoints).
- Stream long outputs.

## Issue tracker

**Linear**, via the claude.ai account connector — check with `/mcp`, where it shows as
*claude.ai Linear*. MCP tools load at session start, so connecting mid-session needs a
restart. Conventions, tool discovery and wayfinding: `docs/agents/issue-tracker.md`.
PRs stay on GitHub.

Branch as `<type>/<TEAM-NUM>-<slug>` (e.g. `feat/ENG-412-vector-store`) so `/code-review`
can resolve the originating ticket mechanically.

## Environment

- Secrets live in `.env` (gitignored); `.env.example` lists the keys. `app.config.Settings`
  is the only reader.
- `GH_TOKEN` needs `repo` + `workflow` scope for PR automation.
- PowerShell: `$env:VAR = "value"`, backtick continues a line, `;` chains — `&&` does not
  work in 5.1. `uv run` needs no `cd` prefix.

## Where commands come from

- `.claude/commands/` and `.claude/skills/` — repo-owned, `uv`-aware: `/plan`,
  `/implement-from-plan`, `/verify`, `/loop-goal`, `/lint`, `/test`, `/run`, `/arch`,
  `/context`, `/retro`. Edit freely.
- **`mattpocock-skills` plugin** (v1.2.1, 25 skills) — `/implement`, `/code-review`, `/tdd`,
  `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/wait-what`. Declared in
  `.claude/settings.json`; files live under `~/.claude/plugins/`. Installed from upstream's
  marketplace (`mattpocock/skills`), not Anthropic's mirror, which lags. Never vendor them
  into the repo.

## Memory

Durable, non-obvious facts go in `~/.claude/projects/<project-slug>/memory/` — one fact per
file, pointer line in `MEMORY.md`. Save decisions, constraints and friction lessons; leave
anything the repo already records to the repo. `/retro` captures a lesson; `/context` audits.

When compacting, preserve the list of modified files and the commands needed to verify them.
