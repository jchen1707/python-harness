# Conventions — `services/`

Business logic and orchestration. A service decides what happens. It does not know about
HTTP, and it does not write SQL.

AI capabilities are **not** here. Retrieval, reranking, agent orchestration and their
evals live in `../ai/`, which is its own layer. See `../ai/AGENTS.md` for why.

## Dependency rule

`services` imports `ai`, `repositories` and `core`. It must not import `api`. A service
that imports `Request`, `HTTPException` or any FastAPI type is in the wrong layer.

A service orchestrates a workflow and may call into `ai/` for a capability. The reverse is
a defect: `ai/` must never import a service.

## Rules

- Accept and return Pydantic models or plain domain types. Do not accept a `Request`.
- Depend on the protocol, not the implementation. A service takes an `Embedder`; it does
  not construct a `VoyageEmbedder`.
- Inject dependencies through the constructor. Do not import a singleton.
- Raise domain errors from `core/errors.py`. Do not raise `HTTPException`.
- Keep one service focused on one resource or one workflow. A service that grows past a
  few hundred lines is usually two services.
- Use `async def` when the method awaits I/O. Use `def` when it computes in memory.
- Offload CPU-heavy work with `asyncio.to_thread`. Chunking, tokenising and parsing block
  the event loop.

## Concurrency

- Bound every fan-out. Wrap `asyncio.gather` over a caller-supplied list with a
  `Semaphore`, or the size of one request becomes the size of the load.
- Prefer `asyncio.TaskGroup` over bare `gather`. It cancels siblings when one task fails
  and propagates the first exception.
- Never hold a lock across an `await` unless you intend to serialise that section.

## Transactions

The service owns the transaction boundary, because only the service knows which
repository calls must succeed together. Pass the unit of work into the repositories;
do not let each repository open its own transaction.

## Observability

Emit a metric for every externally visible operation, and a log line for every decision
that is not obvious from the metric. Record the reason a request was rejected, not only
that it was.
