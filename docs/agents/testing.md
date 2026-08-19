# Testing — this repo

<!-- harness:agnostic -->

**Shared doctrine lives in `.agents/vendor/harness/docs/agents/testing.md`** — the rules that
hold in every stack, and why `test-writer` is defined per stack rather than shared. It is
vendored from [`harness`](https://github.com/jchen1707/harness) and pinned by sha; read it
first.

<!-- /harness:agnostic -->
<!-- harness:claude
**Shared doctrine is provided by the `harness` plugin**, at
`${CLAUDE_PLUGIN_ROOT}/docs/agents/testing.md` — the rules that hold in every stack, and why
`test-writer` is defined per stack rather than shared. Read it first.
/harness:claude -->

This file records only what is true in **this** repo.

## Where tests go

- `tests/` — unit tests. **Offline**: no network, no database. Use fakes and stubs
  (`FakeEmbedder`, an in-memory `VectorStore`, a stubbed `ChatAnthropic`). This is the default
  `uv run pytest` run.
- `tests/integration/` — testcontainers tests against ephemeral pgvector, marked
  `@pytest.mark.integration`. `addopts` excludes the marker, so these run only on request and
  not in the standard CI job.

## The stack rules

1. **Seams here** are a route, a service method, or a repository protocol. Never assert on a
   private helper.
2. **Async tests** use `pytest-asyncio`, with `asyncio_mode = "auto"`.
3. **Type the fixtures and helpers** — `mypy` runs with `disallow_untyped_defs` over `tests`,
   so an untyped helper fails a gate rather than reading as a style note.
4. **Name each test as a sentence**: `test_search_returns_empty_when_no_match`.
5. For each `Settings` field, cover three distinct cases: absent, present but empty, invalid.

## Finishing

`uv run pytest`, and paste the output. For failing tests that encode a spec, quote the
assertion error to show they fail for the intended reason.
