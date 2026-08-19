# Design checklist — python-harness

The stack half of the shared `design-reviewer` frame. The frame carries the depth vocabulary
and the requirement to name a concrete cost; this is what the boundaries actually are here.

## The boundaries this repo has committed to

`api` → `services` → `ai` → `repositories` → `config`, with `ai/evals/` free to import any
layer and imported by nothing. The layers are the seams, and a design finding is about whether
a change respects them or whether the seam itself is now in the wrong place.

What a layer publishes is its module interface. `repositories/` publishes protocols —
`Embedder`, `VectorStore`, `Tool` — and those are the contract every layer above codes
against. A design that makes a caller depend on a concrete implementation has moved the seam
without saying so.

## Shapes that recur here

- A service that constructs its own client rather than receiving one: the seam between
  "decide" and "talk to the outside" has collapsed.
- A repository that returns a driver-specific row object, so every caller learns the schema.
- A `Settings` field read deep inside a call chain rather than injected at the edge.
- LangGraph state that carries a decision another node re-derives.
- A `top-k`, a chunk size or a model id threaded through five signatures because no module
  would own the default.

`docs/architecture.md`'s "Choosing an architecture & design patterns" section is the
per-feature decision record. A design finding that contradicts a recorded decision is a
finding about the record — say so rather than relitigating it in a review.
