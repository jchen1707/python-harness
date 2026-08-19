# Test-review checklist — python-harness

The stack half of the shared `test-reviewer` frame. The frame carries the classes of bad
test; this is what each one looks like here, and which tier owns what.

## The tiers, and their isolation

- `tests/` — unit tests. **Offline**: no network, no database. Fakes and stubs
  (`FakeEmbedder`, an in-memory `VectorStore`, a stubbed `ChatAnthropic`). This is the default
  `uv run pytest` run.
- `tests/integration/` — testcontainers tests against ephemeral pgvector, marked
  `@pytest.mark.integration`. `addopts` excludes the marker, so these do **not** run by
  default or in the standard CI job.

**An unmarked integration test is a finding.** Anything needing network, Docker or a real DB
without the marker breaks the offline run for everyone — and it does so on someone else's
machine, not on the author's.

The inverse is also a finding, and a quieter one: because the default run excludes the marker,
a change with no integration coverage produces exactly the same green as one with it. Say
which you are looking at.

## Stack-specific shapes

- **Public boundary** here means a route, a service method, or a repository protocol. A test
  reaching into a private helper is testing an implementation detail.
- **Async tests** use `pytest-asyncio` with `asyncio_mode = "auto"`. A coroutine test that is
  never awaited passes without running.
- **Typed fixtures** — `mypy` runs with `disallow_untyped_defs` over `tests`, so an untyped
  helper is a gate failure, not a style note.
- **Failure modes worth naming**: validation errors from Pydantic, not-found, empty input,
  bounds on limits and vector `k`, cancellation.
