# Simplicity checklist — python-harness

The stack half of the shared `simplicity-reviewer` frame. The frame carries what counts as a
cut and how to weigh one; this is what is mandated here and therefore must never be reported
as speculation.

## Mandated, not speculative

This repo requires protocols for `Embedder`, `VectorStore` and `Tool` specifically. They are a
documented standard in `docs/architecture.md`, not an abstraction someone added for a future
that may not arrive. **Do not flag them**, even when one has a single implementation — that is
the design, and reporting it teaches the author to ignore this axis.

The same holds for Pydantic models on I/O surfaces. A model that looks like a thin wrapper
over a dict is the boundary the architecture asks for.

## What to look for here

- **Speculative generality** — parameters, config options and hooks added for needs no spec
  asked for.
- **An interface with one implementation and no test double**, outside the three protocols
  above.
- **Duplicated logic** in the diff where extracting is genuinely smaller than leaving it.
- **Dead code** — unreachable branches, unused params, functions nothing calls, flags always
  passed the same value.
- **Pass-through wrappers** — a function or class that only forwards to another.
- **Defensive checks for impossible states** — validating what the type system or a Pydantic
  model already guarantees.

Style and formatting are ruff's. Do not report them.
