# Architectural standards — python-harness

Detailed standards for code in `src/app/`. CLAUDE.md has the summary; this is the
authoritative reference (load with `/arch`; checked by `/review`).

## Choosing an architecture & design patterns (do this during research)
This document is living, not fixed. Before building a non-trivial feature, select — during
the research phase — the architectural style that best fits the problem, then update this
file to codify the chosen style's standards. The repo defaults to a **layered**
architecture with the **repository** pattern (Controller → Service → Repository, §1),
which suits backend web + RAG + agent work, but evaluate alternatives per feature and
adopt or blend where they fit better:
- **Layered** — default; separates transport, business logic, and data access. Use for
  request/response APIs and most services.
- **Repository** — data access behind interfaces (§2); already baked in for the
  vector/embeddings stores. Use whenever logic must stay storage-agnostic.
- **Pipe–filter** — compose independent stages over a stream/batch. Natural fit for RAG
  ingestion (load → chunk → embed → upsert) and ETL-style transforms; model each stage as
  a pure, independently testable filter.
- **Implicit invocation (event-driven / pub-sub)** — decouple producers from consumers via
  events. Use for reactive flows, background processing, and fan-out where the caller
  should not know its handlers.

After selecting a style, **update this file**: document the chosen style's boundaries and
the **design patterns** you will apply, grouped GoF-style —
- *Creational* — e.g. factory for app/agent construction, builder for graph assembly.
- *Structural* — e.g. adapter for external SDKs behind our protocols (§2), facade for
  service entrypoints.
- *Behavioral* — e.g. strategy for swappable `Embedder`/`VectorStore` impls, observer for
  the event-driven flows above.

Keep §1's layering invariant unless a specific feature justifies a documented exception.

## 1. Layering — Controller → Service → Repository
Three layers, one direction:
```
controller (api)  ──▶  service (services)  ──▶  repository (repositories)  ──▶  config
```
- **Controller layer** — `api/`: the entrypoint. FastAPI routers + route functions +
  Pydantic request/response models. Transport only: parse/validate input, call one
  service, shape the response. No business logic, no direct DB/SDK calls.
- **Service layer** — `services/`: business logic. Orchestrates repositories and
  external capabilities, applies domain rules, drives agent/RAG workflows. Agent
  orchestration (LangGraph) lives in `services/agents/`; RAG retrieval orchestration
  in `services/retrieval.py` (or `services/rag/`); domain services in
  `services/<domain>.py`.
- **Repository layer** — `repositories/`: data access, behind interfaces. The
  `VectorStore` (pgvector / in-memory) in `repositories/vector.py`; the embeddings
  client/gateway (`VoyageEmbedder`, `FakeEmbedder`) in `repositories/embeddings.py`;
  relational data access in `repositories/<entity>.py`.
- `core/` — cross-cutting (structlog, error types, middleware). `config.py` — the
  single source of env/secrets. `main.py` — the FastAPI app factory + lifespan.
- **No reverse or lateral dependencies.** Controllers call services only. Services
  call repositories (and `core`/`config`). Repositories call `config` (for DSNs) and
  `core` — never services or controllers. `agents` and `rag` are *capabilities*, not
  layers: agent orchestration is a service; embeddings/vector-store are repositories;
  retrieval is a service that composes them. Compose capabilities at the controller or
  via injected interfaces, never by importing across domains' internals.

## 2. Interfaces over implementations (swappable dependencies)
Define a `Protocol` for each external capability; write at least one impl; inject.
- `Embedder` (`embed(texts) -> list[list[float]]`, `dim() -> int`) in
  `repositories/embeddings.py`: `VoyageEmbedder` (prod), `FakeEmbedder` (tests, offline).
- `VectorStore` (`add(ids, texts, vectors, metadatas)`, `query(vector, k) -> list[Hit]`)
  in `repositories/vector.py`: `InMemoryVectorStore` (tests/quickstart),
  `PgVectorStore` (prod, pgvector).
- `Tool` (agent tools): name + description + input schema + `run(input) -> str`, as
  LangChain tools (`@tool` / `StructuredTool`) with Pydantic input models.
Depend on the protocol, not the class. Wire concrete impls at composition time (app
factory or a `providers`/`services` wiring module), never at call sites.

## 3. Async by default for I/O, sync where simpler
This workload (FastAPI web + RAG + agents) is I/O-bound, so **async is the default for
request handling and I/O** — but async is a tool for concurrency, **not a blanket rule**.
Apply judgment; the `/plan` Approach must state and justify the sync/async boundary for
non-trivial features.
- **Default to async for I/O paths**: FastAPI handlers, HTTP (`httpx.AsyncClient`), DB
  (asyncpg / psycopg async), and embeddings/LLM calls are `async def` so concurrent
  requests don't serialize.
- **Use plain `def` where async buys nothing**: pure CPU-bound or in-memory business
  logic, simple transforms, and helpers with no I/O stay synchronous. Don't write
  `async def` that never `await`s concurrent work — function-coloring has a real cost.
- **Don't fake-async blocking code**: a sync-only library or CPU-bound work called from an
  async path is offloaded with `await asyncio.to_thread(fn, ...)` (see §13), never wrapped
  in an `async def` that blocks the event loop.
- `pytest-asyncio` with `asyncio_mode=auto`; write async tests as `async def`, sync tests
  as plain `def`.

## 4. Pydantic for all I/O
- FastAPI request/response bodies, agent tool inputs, and external service DTOs are
  Pydantic v2 models.
- `config.py` uses `pydantic-settings.BaseSettings` with
  `SettingsConfigDict(env_file=".env")`.
- Validate at the boundary; pass validated objects downstream, not raw dicts.

## 5. Config & secrets
- `app.config.Settings` is the ONLY place env/secrets are read.
- `get_settings()` cached (`functools.lru_cache`); inject `Settings` (or fields) into
  dependents — never call `os.environ` or read `.env` elsewhere.
- Never hardcode API keys. `.env` is gitignored; `.env.example` lists required vars.
- For FastAPI, expose settings via `Depends(get_settings)`.

## 6. Logging & errors
- `structlog` configured once in `core/logging.py` (called from the app factory).
- Use bound loggers with context (`log = structlog.get_logger(); log.bind(...)`). For
  concurrent attribution, bind a `request_id`/`task_id` and propagate via `contextvars`
  (structlog integrates with them).
- Never `print()`. Never swallow exceptions (`except: pass`). Define error types in
  `core/` and map them to HTTP responses in `api/` (or a handler middleware).

## 7. Types
- Every public function has typed params and return. mypy `disallow_untyped_defs=true`.
- `ignore_missing_imports=true` is a pragmatic baseline for stubless third-party libs;
  prefer `[[tool.mypy.overrides]]` per-module when a lib gains types. Annotate every
  `# type: ignore` with a reason.

## 8. Testing
- **Unit tests are offline** (default `uv run pytest`): no network, no DB, no
  containers. Use fakes/stubs (`FakeEmbedder`, in-memory vector store, a stubbed
  `ChatAnthropic`). Fast and hermetic.
- **Integration tests use testcontainers** (`uv run pytest -m integration`): spin up an
  ephemeral **Postgres + pgvector** container, apply the schema, and **insert seed data
  at container instantiation**. A per-test fixture (`clean_db`) **resets the data between
  tests** (truncate + re-seed) so each test starts from the known seed state and
  test-written data never leaks across tests. See `tests/conftest.py` for the fixtures
  and `tests/integration/` for a worked example.
- Integration tests are marked `integration` and excluded from the default run so CI
  stays fast and doesn't require Docker. Run them locally after `uv sync --extra app`.
- Test fixtures may use **synchronous** DB drivers (e.g. sync `psycopg`) for
  setup/seed/teardown — the async-first rule (§3) governs application I/O paths, not
  test-harness code. Keep such imports lazy so the default offline run stays import-free.
- Naming: `tests/<layer>/test_<thing>.py`; integration tests under `tests/integration/`.
- Coverage is opt-in: `uv run pytest --cov=app --cov-report=term-missing`.

## 9. Agent standard (LangGraph + langchain-anthropic) — lives in `services/agents/`
- Model via `langchain_anthropic.ChatAnthropic(model=settings.anthropic_model)`. Do NOT
  pass `temperature`/`top_p`/`top_k` (removed on Opus 4.7/4.8/Fable 5).
- Enable adaptive thinking for non-trivial graphs; prompt-cache the system prompt.
- Prefer `langgraph.graph.StateGraph` + `MessagesState` + `ToolNode` + `tools_condition`
  for custom orchestration; use `langgraph.prebuilt.create_react_agent` for the simple
  ReAct case. (If the prebuilt API churns, the `StateGraph` form stays stable — prefer
  it for longevity; LangGraph is on 1.x, so pin and re-check on upgrade.)
- Tools are LangChain tools (`@tool` / `StructuredTool`) with Pydantic input models.
- Keep LLM construction in `services/agents/` (or a `providers` module); inject into
  graphs. Services call repositories for any data the agent needs.

## 10. RAG standard — repositories hold data access, services orchestrate retrieval
- `repositories/embeddings.py`: `Embedder` protocol + `VoyageEmbedder` + `FakeEmbedder`.
- `repositories/vector.py`: `VectorStore` protocol + `InMemoryVectorStore` +
  `PgVectorStore` (psycopg + `pgvector` adapter; table/collection from `Settings.pgvector_*`).
- `services/retrieval.py`: `index_documents(store, embedder, docs)` +
  `retrieve(store, embedder, query, k=5)` — compose the two interfaces; depend on
  protocols.
- Vector dim must match the embedder (`embedder.dim()`); assert at init.

## 11. Containerization standard
- Local dev DB: `docker compose up -d db` (Postgres + pgvector; see `docker-compose.yml`).
- When containerizing the app: a multi-stage Dockerfile (uv build → slim runtime),
  non-root user, healthcheck on `/healthz`. Add an `app` service to `docker-compose.yml`
  that depends on `db`. Keep images reproducible (pin the `pgvector/pgvector:pg16` tag
  already used). Integration tests use their own ephemeral container (testcontainers),
  not this compose file.

## 12. Dependency policy
- The approved stack is declared in `pyproject.toml`
  `[project.optional-dependencies].app`. `testcontainers` is a dev dependency (for
  integration tests). Adding a NEW framework/library outside the standard requires
  updating this file AND CLAUDE.md's "Standard stack" first — do not silently `uv add`
  alternatives.
- `uv add` / `uv pip install` are not pre-approved; they change the standard. Prefer
  editing `pyproject.toml` directly, then `uv lock` / `uv sync`.

## 13. Concurrency (Python / asyncio)
The app is async-first (FastAPI + asyncio). Follow these to stay correct under load:
- **Never block the event loop.** In `async def` code, any call that can block — sync DB
  drivers, CPU-bound work, `requests`, `time.sleep`, slow file I/O — must be offloaded
  with `await asyncio.to_thread(fn, ...)` or `loop.run_in_executor(...)`. Use
  async-native clients (`httpx.AsyncClient`, asyncpg / psycopg async, the embeddings
  client's async path).
- **Structured concurrency over ad-hoc tasks.** Prefer `asyncio.TaskGroup` (3.11+) to
  fan out and await child tasks together — it propagates the first exception and
  cancels siblings. Avoid `asyncio.create_task` fire-and-forget; if you must, keep a
  strong reference (an unreferenced task can be garbage-collected mid-flight) and
  `await` or cancel it.
- **Guard shared mutable state.** A single asyncio loop is single-threaded, so state is
  safe across `await`-free sections — but anything touched by multiple tasks or threads
  needs `asyncio.Lock` (async) / `threading.Lock` (threads) or copy-on-read. Treat the
  GIL as a guard against data races, not a substitute for locks around non-atomic
  compound operations.
- **Bound and queue concurrent work.** Use `asyncio.Semaphore` to cap concurrent calls to
  a bounded resource (DB pool, rate-limited API). Apply backpressure with a bounded
  `asyncio.Queue`, not an unbounded buffer. Always set timeouts: `httpx.AsyncClient(
  timeout=...)` and `asyncio.wait_for(...)` for ad-hoc awaits.
- **Connection pools, not per-call connections.** Create one pool at startup (lifespan),
  share it, close it at shutdown. Acquire via `async with pool:` so connections return
  even on error.
- **Cancellation is expected.** Write coroutines to be cancel-safe: release resources in
  `finally` / async context managers; use `anyio`'s `fail_after` / `CancelScope` when you
  must complete cleanup. Don't swallow `asyncio.CancelledError`.
- **Threads vs processes.** I/O concurrency → asyncio. CPU-bound parallelism → a process
  pool (`loop.run_in_executor(ProcessPoolExecutor(), ...)`) or `multiprocessing`, since
  the GIL serializes Python bytecode across threads. Keep CPU workers stateless and
  return results, not shared memory.
- **Logging under concurrency.** Bind a `request_id`/`task_id` at the handler and
  propagate via `contextvars` (not thread-local) so concurrent log lines are
  attributable; structlog reads `contextvars` automatically.

### Threading (`threading` module) — best practices
asyncio is the default for I/O concurrency; reach for OS threads only for blocking work you
cannot avoid (sync-only SDKs, blocking file I/O) or to bridge sync↔async. When you do:
- **Offload from async code via `asyncio.to_thread(fn, ...)`** (or
  `loop.run_in_executor(pool, ...)`) instead of spawning raw `Thread`s inside a handler —
  it integrates with the event loop and cancellation.
- **Use a bounded `ThreadPoolExecutor`**, not unbounded `Thread()` spawning; size it for
  the backing resource (e.g. a DB pool), create it at startup, and shut it down on exit.
- **Guard shared mutable state** with `threading.Lock`/`RLock`. The GIL prevents data
  races on a single bytecode but NOT on compound read-modify-write — lock those. Prefer
  immutable messages and `queue.Queue` for thread-to-thread handoff over shared globals.
- **Don't expect CPU parallelism from threads** — the GIL serializes Python bytecode; use
  `ProcessPoolExecutor`/`multiprocessing` for CPU-bound work. Threads help only when work
  releases the GIL (most blocking I/O, many C extensions).
- **Never touch the event loop or asyncio objects from a worker thread** except via
  `loop.call_soon_threadsafe(...)` or `asyncio.run_coroutine_threadsafe(...)`.
- **Join threads / use daemon threads on shutdown** and propagate exceptions back to the
  caller — a bare `Thread` swallows them, whereas `Future.result()` from an executor
  re-raises.