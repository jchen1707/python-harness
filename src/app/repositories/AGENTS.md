# Conventions — `repositories/`

Data access, and the protocols that describe it. This layer talks to Postgres, pgvector
and external APIs. It holds no business rules.

## Dependency rule

`repositories` imports `core` only. It must not import `services` or `api`. A repository
does not know why it is being called.

## Protocols come first

Define the interface here as a `typing.Protocol`, then write the implementation beside it.
Services depend on the protocol, never on the concrete class.

The three the architecture requires: `Embedder`, `VectorStore`, `Tool`.

- Keep a protocol small. Methods a caller never uses are methods a fake must still write.
- Return domain types or Pydantic models. Never return a driver row, a cursor or an
  `httpx.Response`. A leaked driver type ties every caller to the driver.
- Name a method for what it does, not how: `get_by_id`, not `select_one`.

## SQL

- Always use bound parameters. Never build SQL with an f-string or `%` formatting, even
  for an identifier you believe is safe.
- Select the columns you use. `SELECT *` moves data you discard, and it breaks when the
  schema changes.
- Set a `LIMIT` on every query that can return more than one row.
- Batch related work. A query inside a loop over another query's results is an N+1 and
  will not scale.
- Add an index for every new filter, join or `ORDER BY` column. Put the index in the
  migration, not in a comment.
- Never edit a migration that has been applied. Write a new one.

## pgvector

- Create an index for vector search. Without one, every query scans every row.
- Choose the index type for the workload. HNSW gives better recall and costs more memory.
  IVFFlat builds faster and needs its list count tuned to the row count.
- Match the distance operator to the index. An index built for cosine distance does not
  serve an L2 query.
- Store the embedding model name and dimension with the vector. A model change makes old
  vectors invalid, and you must be able to find them.
- Fetch the smallest `top-k` that answers the question. Retrieving 200 rows to use 5 costs
  latency and memory in every request.

## Connections

- Use one pooled connection source, built at startup. Do not open a connection per call.
- Size the pool deliberately. A pool larger than the database allows will fail under load.
- Set a statement timeout. A query with no timeout can hold a connection indefinitely.

## Async

Use `async def` for database and network calls. Use `psycopg` in async mode. If a driver
is synchronous, wrap the call in `asyncio.to_thread`. Never block the event loop.

## Tests

Unit tests use in-memory fakes that satisfy the protocol. Tests that need real SQL or real
pgvector behaviour are integration tests and use testcontainers. See `tests/AGENTS.md`.
