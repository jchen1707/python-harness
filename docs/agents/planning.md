# Planning — this repo

<!-- harness:agnostic -->

**Shared doctrine lives in `.agents/vendor/harness/commands/plan.md` and
`implement-from-plan.md`** — the two-terminal protocol, the branch setup, the sign-off
checkpoint, the deviations rule. It is vendored from
[`harness`](https://github.com/jchen1707/harness) and pinned by sha; read it first.

<!-- /harness:agnostic -->
<!-- harness:claude
**Shared doctrine is provided by the `harness` plugin**, as `/plan` and
`/implement-from-plan` — the two-terminal protocol, the branch setup, the sign-off
checkpoint, the deviations rule. Read them first.
/harness:claude -->

This file records only what is true in **this** repo.

## What a design has to state explicitly

`/plan` step 4 requires all of these before sign-off. A plan missing one hands terminal 2 a
decision it will make silently and differently.

- **Layer placement.** Which of `api` → `services` → `ai` → `repositories` → `config` each
  piece belongs to, and which existing module it extends.
- **The protocols to define or extend.** `Embedder`, `VectorStore` and `Tool` live in
  `repositories/`; anything new that will have more than one implementation, or a test double,
  belongs beside them.
- **The sync/async boundary, and why.** Which pieces are `async def` and which stay plain
  `def`. Async is for I/O; blanket `async def` buys nothing and costs an event loop. See
  `docs/architecture.md` §3. State it as a decision, not as an outcome.
- **The pattern chosen for the feature**, per `docs/architecture.md`'s "Choosing an
  architecture & design patterns" section, which is this repo's per-feature decision record.
- **Migrations**, where a new access path needs an index.

## Where code lands

`src/app/<layer>/`, and each layer directory carries its own path-scoped `AGENTS.md`. Read the
one for the layer you are editing before the first edit — an agent working in `api/` never
loads `repositories/AGENTS.md`, so its conventions have to be fetched deliberately.

Application code needs the approved stack installed: `uv sync --extra app`.

## Test tiers, for the test plan

- `tests/` — offline unit tests, the default `uv run pytest` run. Fakes and stubs only.
- `tests/integration/` — testcontainers against ephemeral pgvector, marked
  `@pytest.mark.integration`, excluded from the default run by `addopts`.

For each `Settings` field the change adds, the test plan lists three distinct cases: absent,
present but empty, and invalid value.

## Before a PR

There is no pre-PR skill here yet, and no PR template. Fill the body from the plan and the
`/verify` output, and sync the tracker in the same turn — `docs/agents/issue-tracker.md`
→ Status sync.
