# Architectural standards — python-harness

**Cross-cutting rules and approved feature decisions only.** Every rule here holds in every
directory. Feature decisions document narrow exceptions without changing the general rules.
Rules that apply to one layer live in that layer's `AGENTS.md`, next to the code they govern.

This file exists because nested `AGENTS.md` files are **path-scoped**: an agent working in
`api/` does not load `repositories/AGENTS.md`. An invariant that spans layers must live
here, or it stops being enforced exactly where it matters.

Load with `/arch`. `/code-review` reads this file plus `AGENTS.md` as the Standards axis.

## Where the per-layer rules live

| Directory | Owns |
| --- | --- |
| `src/app/api/AGENTS.md` | HTTP edge, status codes, pagination, dependency injection |
| `src/app/core/AGENTS.md` | Settings, structlog, Prometheus metrics, error types, retries |
| `src/app/repositories/AGENTS.md` | SQL, pgvector indexes, protocols, connection pools |
| `src/app/services/AGENTS.md` | Orchestration, transaction boundaries, fan-out limits |
| `src/app/ai/AGENTS.md` | Why AI is its own layer; rules for all of it |
| `src/app/ai/retrieval/AGENTS.md` | Chunking, embedding, hybrid search, filtering |
| `src/app/ai/reranking/AGENTS.md` | Cross-encoders, fusion, diversity, fallback |
| `src/app/ai/agents/AGENTS.md` | LangGraph, prompt caching, tools, token budgets |
| `src/app/ai/evals/AGENTS.md` | Datasets, metrics per layer, when to run |
| `tests/AGENTS.md` | Unit vs integration, seams, fakes, determinism |

## Choose the architecture during research

This document is living. Before you build a non-trivial feature, choose the architectural
style in the research phase, then record it here. Do not choose it while writing code.

The repo defaults to a **layered** architecture with the **repository** pattern. It suits
backend web, RAG and agent work. Consider these alternatives per feature:

- **Layered** — the default. Separates transport, business logic and data access.
- **Repository** — data access behind an interface. Use when logic must stay
  storage-agnostic.
- **Pipe and filter** — independent stages over a stream or batch. It fits RAG ingestion
  (load, chunk, embed, upsert). Make each stage pure and testable on its own.
- **Event-driven** — decouples producers from consumers. Use for background work and
  fan-out, where the caller must not know its handlers.

Record the design patterns you apply, grouped as creational, structural and behavioural.
Keep the layering invariant below unless a feature justifies a documented exception.

## Feature decisions

### BAC-2 support document retrieval

- **Creational:** The app factory wires each concrete dependency to its protocol.
- **Structural:** The feature uses the repository pattern and the repository's layered
  architecture.
- **Behavioural:** PDF ingestion uses pipe and filter.
  The filters run in this order: extract, chunk, embed, and store.
  Keep each filter pure where possible.
  Test each filter separately.

Chunking uses fixed-size word windows inside each page.
This choice deviates from the structure-first rule in `src/app/ai/retrieval/AGENTS.md`.
Fixed windows can split sentences.
The 25-word overlap reduces this boundary loss.
The approved proof of concept accepts this quality cost for deterministic chunks.

The expected load is approximately 150 chunks and 30 users.
The Voyage ingest rate limit is the main constraint.

The proof of concept uses dense vector search only.
This choice deviates from the hybrid search rule in `src/app/ai/retrieval/AGENTS.md`.
Dense search reduces recall for identifiers, error codes, and rare words.
The team accepts this cost to deliver the proof of concept in one week.

The proof of concept uses structured logs without Prometheus RED metrics.
This choice deviates from the metrics rule in `src/app/core/AGENTS.md`.
The approved stack does not include `prometheus-client`.
The team defers that dependency to deliver the proof of concept in one week.

## 1. Layering

One direction, no exceptions but the one named below:

```
api  ──▶  services  ──▶  ai  ──▶  repositories  ──▶  config
```

- **No reverse dependency.** A repository must never import a service.
- **No lateral dependency.** Two services must not import each other's internals. Compose
  them at the layer above, or behind an injected interface.
- `core/` is cross-cutting. Every layer may import it. It imports none of them.
- `ai/` is the applied-AI capability layer: retrieval, reranking, agents. `services` may
  call into it; it must never import a service. Its data access belongs in
  `repositories/`. See `src/app/ai/AGENTS.md` for why it is separate from `services`.
- `ai/evals/` sits outside the request path. It may import any layer; nothing imports it.
  This is the one documented exception to the direction above, and it holds because evals
  never runs in a request.

## 2. Depend on protocols, not classes

Define a `typing.Protocol` for every external capability. Write at least one
implementation. Inject it.

The required three: `Embedder`, `VectorStore`, `Tool`. All live in `repositories/`.

Wire concrete implementations once, at composition time in the app factory. Never
construct one at a call site.

## 3. Types

Type every public function: parameters and return. `mypy` runs with
`disallow_untyped_defs`. Prefer a precise type over `Any`. A `# type: ignore` needs a
comment that says why.

## 4. Scaling

Design for the load you expect, and state the number.

- **Know the bound.** Every feature is limited by something: connections, memory, tokens
  or an upstream rate limit. Name it before you build.
- **Bound every queue and every fan-out.** An unbounded buffer converts a traffic spike
  into an out-of-memory failure. Apply backpressure with a bounded `asyncio.Queue`.
- **Paginate every list.** An endpoint that returns all rows works until the table grows.
- **Pool connections.** Create one pool at startup and share it. Size it to the database,
  not to the traffic.
- **Set a timeout on every outbound call**, and a statement timeout on every query.
- **Cache what is expensive and stable**: embeddings, static prompt prefixes, reference
  data. Give every cache entry an explicit lifetime and a size limit.
- **Make work idempotent** so a retry is safe and a queue can deliver more than once.
- **Keep the request path stateless.** State in a process prevents horizontal scaling.
- **Measure before you optimise.** A performance change without a measurement is a guess.
  See `evals/AGENTS.md` for AI paths, and the RED and USE methods in `core/AGENTS.md`.

## 5. Extensibility

- **Add behind an existing protocol first.** A new implementation of `VectorStore` needs
  no new abstraction.
- **Do not add an abstraction for one implementation.** Wait for the second. An interface
  with one implementation and no test double is indirection that pays nothing.
- **Keep the extension point narrow.** A small protocol is easy to satisfy. A large one
  forces every implementer to write methods nobody calls.
- **Version an external contract, never break it.** Add a field; do not repurpose one.
  Deprecate with a date and a replacement, and log every use of the deprecated path.
- **Configuration is an extension point too.** Every new flag is a branch that must be
  tested. Prefer a sensible default the module owns.

## 6. Concurrency

The app is async-first. These rules stay here because they cross layers.

- **Never block the event loop.** Offload a blocking call with `asyncio.to_thread`.
- **Prefer `asyncio.TaskGroup` to bare `gather`.** It cancels siblings on failure and
  propagates the first exception.
- **Bound concurrency with a `Semaphore`** sized to the backing resource.
- **Cancellation is expected.** Release resources in `finally`. Never swallow
  `asyncio.CancelledError`.
- **Threads do not give CPU parallelism.** The GIL serialises Python bytecode. Use a
  process pool for CPU-bound work. Use threads only for blocking I/O you cannot avoid.
- **Never touch the event loop from a worker thread**, except through
  `loop.call_soon_threadsafe` or `asyncio.run_coroutine_threadsafe`.
- **Guard compound read-modify-write with a lock.** The GIL does not make it atomic.
- **Propagate context with `contextvars`, not thread-locals**, so concurrent log lines
  stay attributable.

## 7. Containers

- Local development database: `docker compose up -d db` (Postgres with pgvector).
- To containerise the app: multi-stage Dockerfile (uv build, then a slim runtime),
  non-root user, healthcheck on `/healthz`. Pin the image tag.
- Integration tests use their own ephemeral container through testcontainers. They do not
  use the compose file.

## 8. Dependency policy

The `[project.optional-dependencies].app` table in `pyproject.toml` approves application
libraries.
The `[dependency-groups].dev` table approves development tools.

`pypdf` reads uploaded PDFs in the request path, so it belongs in the `app` extra.
`fpdf2` lays out the mock corpus PDFs, so it belongs in the development group.
A PDF reader does not replace the document layout features in the development writer.

A new framework or library outside that set requires an update to this file **and** to
`AGENTS.md` first. Do not run `uv add` to introduce an alternative. Edit `pyproject.toml`,
then run `uv lock` and `uv sync`.
