# Conventions — `tests/`

## The two suites

| Suite | Command | Rule |
| --- | --- | --- |
| Unit | `uv run pytest` | Offline. No network, no Docker, no database. |
| Integration | `uv run pytest -m integration` | Real pgvector through testcontainers. |

Mark every test that needs a container, a network call or a real model with
`@pytest.mark.integration`. An unmarked integration test breaks the default run for
everyone, and the default run is what the Stop gate uses.

## What a good test is

A test verifies behaviour through a public interface. Code may change completely; the test
should not.

- Test at the seam, not inside the module. A test that reaches into a private helper
  breaks on every refactor and proves nothing about behaviour.
- Name the test for the behaviour: `test_search_returns_empty_when_below_threshold`. The
  name is the specification.
- Assert on the output, not on the number of calls to a mock. A call-count assertion
  encodes the implementation.
- One behaviour per test. A test with five assertions on five behaviours reports one
  failure and hides four.

## What to avoid

- **Tautological tests.** A test that computes the expected value the way the code does
  will pass whatever the code does.
- **Over-mocking.** A test whose mocks encode the implementation will pass against a
  broken rewrite.
- **Testing the framework.** Do not test that FastAPI validates a Pydantic model, or that
  ruff formats. Test your logic.
- **Assertions on a constant.** `assert True` and `assert 1 == 1` cannot fail.

## Fakes over mocks

Repositories are defined by protocols, so write a fake that satisfies the protocol and
keeps state in a dict. A fake is readable, reusable and behaves like the real thing. Use
`unittest.mock` only to assert that an external side effect happened.

Keep shared fakes in `tests/conftest.py`: `FakeEmbedder`, an in-memory `VectorStore`, a
stubbed chat model.

## Determinism

- Fix every seed.
- Freeze time rather than sleeping. A test that sleeps is slow and still flaky.
- Never call a real model or a real network endpoint in a unit test.
- A flaky test is a failing test. Fix it or delete it; do not rerun it.

## Coverage

Coverage shows which lines ran, not which behaviours are guarded. Use it to find untested
areas, never as a target. A suite at 100% of lines and 0% of edge cases is common.

The Definition of Done asks a sharper question: **would a test fail if this behaviour
regressed?** If you cannot point to one, the behaviour is untested.

## Layout

Mirror the source tree: `tests/services/test_documents.py` tests
`src/app/services/documents.py`. Integration tests live in `tests/integration/`.
