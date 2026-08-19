# Performance checklist — python-harness

The stack half of the shared `perf-reviewer` frame. The frame carries the rule that every
finding names the scale at which it starts to hurt; this is what scales badly here.

- **N+1 queries** — a query inside a loop over the results of another query. The classic, and
  still the most common real finding. Fix by batching or joining.
- **Missing index for a new access path** — a filter, join or `ORDER BY` on a column with no
  index. Check the migration, not just the query.
- **Unbounded result sets** — a query with no `LIMIT` where the row count grows with usage, or
  an endpoint returning a full table with no pagination.
- **Repeated work in a loop** — recomputing an invariant, rebuilding a client, re-reading a
  file or re-parsing config per iteration.
- **Loading more than is used** — `SELECT *` then using two columns; fetching whole rows to
  count them; materialising a full list to take the first item.
- **Quadratic string or list building** — repeated concatenation in a loop where a join would
  be linear.
- **pgvector specifics** — vector search with no index, which is a sequential scan over every
  embedding; an index type or probe/ef setting mismatched to the recall target; an oversized
  `top-k` fetched then discarded; embedding one document per call where the API accepts a
  batch.
- **Sync blocking on a hot path** — flag it and defer to the `async` axis rather than
  double-reporting.

There is no browser and no bundle here. Scale is rows, documents, chunks, tokens and
concurrent requests.
