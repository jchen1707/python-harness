# python-harness

Guardrails, workflow, and standards for Python development in this repo. This is a
**harness, not an application** — it defines *how* to develop here (workflow, linting,
architectural standards, context/memory management), not the app itself. Populate
`src/app/` per `docs/architecture.md`.

Intended workload: **backend web development, RAG applications, and AI agent orchestration.**

## Quick commands
Everything runs through `uv` (cross-platform; Windows/PowerShell-friendly).

| Task | Command | Slash |
| --- | --- | --- |
| Install tooling | `uv sync` | — |
| Install approved app stack | `uv sync --extra app` | — |
| Run tests (unit, offline) | `uv run pytest` | `/test` |
| Run integration tests | `uv run pytest -m integration` (needs Docker + `uv sync --extra app`) | — |
| Lint + format-check + type | `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` | `/lint` |
| Dev server (needs `src/app/main.py`) | `uv run uvicorn app.main:app --reload` | `/run` |
| Plan a feature (terminal 1) | — | `/plan` |
| Implement from plan (terminal 2) | — | `/implement` |
| Standards review of changes | — | `/review` |
| Load architecture standards | — | `/arch` |
| Context/memory hygiene | — | `/context` |
| Capture a lesson from friction | — | `/retro` |

## Standard stack (approved — do not introduce alternatives without updating this file)
- **Python 3.12** managed by **uv**. **Web**: FastAPI + `uvicorn[standard]`.
- **Schemas/config**: Pydantic v2 + `pydantic-settings` (`.env`-driven).
- **HTTP**: `httpx` (async). **Logging**: `structlog`.
- **Agents**: **LangGraph** + `langchain-anthropic** (`ChatAnthropic`), orchestrated in
  `services/agents/`. Default model `claude-opus-4-8`. Adaptive thinking for complex
  steps; prompt-cache static system prompts; stream long outputs.
- **RAG embeddings**: **Voyage AI** (`voyageai`, model `voyage-3`) behind an `Embedder`
  interface in `repositories/embeddings.py`. (Anthropic has no embeddings API.)
- **Vector store**: **Postgres + pgvector** behind a `VectorStore` interface in
  `repositories/vector.py` (dev DB via `docker compose up -d db`). Keep an in-memory
  impl for unit tests.
- **Numerics**: `numpy` for vector math / embedding arrays (used by the embeddings and
  vector-store layers).
- **Testing**: `pytest` + `pytest-asyncio` + `pytest-cov`; **testcontainers** for
  integration tests against a real ephemeral pgvector DB.
- **Lint/format**: `ruff`. **Types**: `mypy` (`disallow_untyped_defs`).
- **Pre-commit**: ruff + mypy + hygiene hooks (`pre-commit install`).
- **CI**: GitHub Actions (ruff, mypy, pytest — unit only; integration run locally).

## Directory layout (standard — put code here, by layer)
```
src/app/
  __init__.py
  config.py        # pydantic-settings Settings — the ONLY place secrets are read
  main.py          # FastAPI app factory + lifespan (created when the app is built)
  core/            # cross-cutting: logging, errors, middleware
  api/             # CONTROLLER layer: FastAPI routers + routes. Entrypoint, transport only.
  services/        # SERVICE layer: business logic + orchestration (agents/, retrieval, ...)
  repositories/    # REPOSITORY layer: data access behind interfaces (vector, embeddings, <entity>)
tests/
  conftest.py        # testcontainers fixtures (integration); unit tests stay offline
  test_smoke.py      # harness self-check
  integration/        # testcontainers integration tests (marked `integration`)
docs/architecture.md  # full architectural standards (load with /arch)
.claude/              # shared Claude Code config (settings.json + commands/)
```

## Development workflow (the loop)
1. **Understand / research** — read the relevant code + `docs/architecture.md` (or
   `/arch`). For non-trivial features, select the architectural style and design patterns
   that fit the problem during this step and update `docs/architecture.md` accordingly
   (see its "Choosing an architecture & design patterns" section).
2. **Plan** — for non-trivial work, agree the approach first: use `/plan` (writes
   `.claude/plans/plan.md` **and** `.claude/plans/test-plan.md`) or enter plan mode.
   Planning always ends with an explicit **user sign-off** checkpoint and then **stops**
   — it does not roll straight into implementing, even in a single terminal or
   autonomous mode. To plan with one model and implement with another, see "Two-terminal
   plan→implement workflow" below.
3. **Implement** — write code in the correct layer; types on every public function.
4. **Sync** — `uv sync` (tooling) + `uv sync --extra app` (approved stack) as needed.
5. **Verify** — `/lint` then `/test` (and `uv run pytest -m integration` for DB-backed
   work) then `/review`. Fix root causes; don't paper over.
6. **Commit** — only when asked; keep changes minimal and per-layer.
7. **Improve (write-back)** — when a step involved non-obvious friction (a bug that
   took real effort, or difficulty using a tool), run `/retro` to capture the lesson
   to memory so it doesn't recur; promote recurring/procedural ones to a command or a
   `CLAUDE.md` / `docs/architecture.md` edit. See "Context & memory management".

### Definition of Done
A change is done only when ALL pass:
- `uv run ruff check .` clean · `uv run ruff format --check .` clean · `uv run mypy` clean
- `uv run pytest` green (and `uv run pytest -m integration` green for DB-backed changes)
- `/review` finds no standards violations
- No secrets in code; no `print()` (use structlog); new behavior has tests
- If the change involved non-obvious friction (a tricky bug or tool difficulty), the
  lesson is captured via `/retro`

## Guardrails
- **Image / visual inputs require explicit permission.** Before starting any task that
  takes an image as input — screenshots, diagrams, photos, scanned or image-based PDFs,
  OCR, or any vision/multimodal model call — STOP and ask the user for explicit
  confirmation before proceeding. Do not begin such work on assumption.

## Two-terminal plan→implement workflow (model switching)
To plan with one model and implement with another (e.g. plan on a Claude Pro terminal,
implement on an API-key terminal), split the loop across two terminals with an explicit
plan file as the handoff:
1. **Terminal 1 (planning model) — `/plan <feature>`**: **first pick the base branch** —
   `/plan` asks which branch to build off of (defaulting to `main`), checks it out, pulls
   the latest, and creates the feature branch off it, so work never starts from a stale
   branch. Then research + plan as a task list, and write `.claude/plans/plan.md`
   (Goal · Context · Approach · numbered Steps ·
   Verification · Open questions) **and** `.claude/plans/test-plan.md` (Scope · unit
   tests · integration tests · edge cases · how to run). Then **get explicit user
   sign-off on both plans** (a required checkpoint — `/plan` asks and waits, even in
   autonomous mode) and **STOP**. Do not implement.
2. **Terminal 2 (implementation model) — `/implement`**: read `.claude/plans/plan.md`
   and `test-plan.md`, build a fresh task list from the Steps + test cases, and
   implement each to the Definition of Done (`/lint` → `/test` → `/review`); update the
   plans as items complete.

`plan.md` and `test-plan.md` are gitignored — local handoff artifacts, not committed.
Plans live in `.claude/plans/` (pinned via `plansDirectory` in `.claude/settings.json`);
plan mode's own auto-saved file uses a random slug name and isn't a reliable handoff, so
`/plan` writes the stable `plan.md` / `test-plan.md` instead.

## Architectural standards (summary — full detail in docs/architecture.md)
- **Choose the architecture during research**: default is layered + repository, but
  evaluate alternatives (pipe–filter, implicit invocation, …) per feature and record the
  choice + applicable design patterns in `docs/architecture.md` before building.
- **Layering (Controller → Service → Repository)**: `api` (controllers/entrypoint) →
  `services` (business logic) → `repositories` (data access) → `config`. No reverse deps.
- **Async by default for I/O, sync where simpler**: default to async for I/O paths
  (FastAPI handlers, `httpx.AsyncClient`, async DB drivers, LLM/embeddings calls), but
  async is for concurrency, not a blanket rule — keep pure CPU/in-memory logic plain
  `def`, and offload blocking calls with `asyncio.to_thread` rather than fake-async. The
  plan must justify the sync/async boundary (see §3).
- **Interfaces over concrete deps**: define `Embedder`, `VectorStore`, `Tool` protocols
  in repositories; services depend on protocols, not classes. Inject; don't hardcode.
- **Concurrency**: never block the event loop; structured concurrency (`TaskGroup`);
  guard shared state; bound work with semaphores; pools not per-call. See §13.
- **Pydantic for all I/O**: request/response models, tool inputs, config.
- **Config & secrets**: read env/secrets ONLY in `app.config.Settings`; inject `Settings`
  (or values) into dependents. Never hardcode keys. `.env` is gitignored.
- **Logging**: `structlog` (bound loggers, `contextvars` for concurrent attribution);
  never `print()`. No swallowed exceptions.
- **Types**: every public function typed; mypy `disallow_untyped_defs=true`.
- **Tests**: unit tests offline (no network/DB — fakes/stubs); integration tests use
  testcontainers (ephemeral pgvector, seed at instantiation, reset between tests).

## Context & memory management
Keep context lean and store durable facts outside it.
- **CLAUDE.md (this file) is the source of truth** for standards/workflow and is loaded
  every session — keep it accurate and concise; don't duplicate it in memory.
- **Detailed standards live in `docs/architecture.md`** (load via `/arch` on demand, not
  every session) to keep the always-loaded context small.
- **Durable, non-obvious facts** (decisions, preferences, constraints not in code or git)
  go in the memory store at
  `C:\Users\jchen\.claude\projects\C--Users-jchen-Documents-python-harness\memory\` — one
  fact per file with frontmatter; add a pointer line in its `MEMORY.md`. Prefer
  `project`/`feedback` types; don't save what the repo already records.
- **Lessons from friction (write-back loop)** — when a bug or tool difficulty took
  real effort, capture it with `/retro`: a `feedback`/`reference` memory (symptom ·
  root cause · how to avoid) so future sessions skip the trap. Recurring or procedural
  lessons get promoted to a slash command or a `CLAUDE.md` / `docs/architecture.md`
  edit. `/context` flags friction you haven't captured yet.
- **Don't re-read files you've already read or edited** — trust file state; the harness
  tracks it. Re-fetch only if the file may have changed externally.
- **Prefer dedicated tools** (Grep/Glob/Read/Edit) over shell for file work; batch
  independent tool calls in one turn.
- **When context grows large**, proactively summarize what's still relevant and drop the
  rest; consider `/context` to audit. Don't wrap up early or hand off mid-task — the
  harness preserves a summary across compaction.
- **Plans** for non-trivial work go in `.claude/plans/` (gitignored; pinned via
  `plansDirectory`). For cross-model handoffs use the `/plan` → `/implement` loop with a
  stable `.claude/plans/plan.md`; update or discard when the work is done.

## Agents & subagents (Claude Code dev workflow)
Claude Code subagents that drive development here — distinct from the LangGraph
*application* agents you build in `services/agents/` (see Model guidance below).
- **When to spawn one**: only when the user asks, or for read-heavy fan-out that pays for a
  fresh context — broad codebase exploration, parallel research across many files. Each
  subagent starts cold and re-derives context, so don't spawn for routine edits or
  multi-step builds that the `/plan` → `/implement` loop already covers.
- **Pick the right type**: `Explore`/`general-purpose` for search and research (read-only
  fan-out), `Plan` for design. Give a focused task and the search breadth ("medium" vs
  "thorough"); relay only the conclusion back into the main context.
- **Reusable subagents**: define custom agent types in `.claude/agents/` (name,
  description, least-privilege tool access, optional model) so they're shareable and
  scoped — prefer the narrowest tool set the task needs.
- **Keep context lean**: subagents return summaries, not file dumps; continue an existing
  subagent rather than re-spawning when you need its accumulated context.

## Model guidance (for agent code built in `services/agents/`)
- Default model **`claude-opus-4-8`** unless the user names another. For high-volume
  routine work, `claude-sonnet-4-6` is a cost-conscious override (set `ANTHROPIC_MODEL`).
- **Adaptive thinking**: `thinking: {type: "adaptive"}` for complex reasoning. Do NOT
  pass `temperature`/`top_p`/`top_k` or `budget_tokens` (removed/400 on Opus 4.8/Fable 5).
- **Prompt caching**: cache static system prompts (`cache_control: ephemeral`, max 4
  breakpoints) — big savings on repeated agent invocations.
- **Stream** long outputs; use the SDK's `.get_final_message()` if you don't need
  per-event handling.
- Configure the model via `app.config.Settings.anthropic_model`, not inline strings.

## Env & secrets
Copy `.env.example` → `.env` and fill in. `.env` is gitignored — never commit it. All
keys are read by `app.config.Settings` (pydantic-settings); never hardcode them in code.
`GH_TOKEN` is for the `gh` CLI / GitHub API (PR and release automation) — needs
`repo` + `workflow` scopes (classic PAT) or Contents/Pull-requests/Workflows RW (fine-grained).

## Windows / PowerShell notes
- Use `uv run <cmd>` for everything — do not prefix with `cd` (cwd is already set).
- Env vars in shells: `$env:VAR = "value"`; line continuation is the backtick `` ` ``.
- No `&&` chaining in PowerShell 5.1 — use `;` or `if ($?) { ... }`.
