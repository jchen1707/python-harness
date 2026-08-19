# Standards checklist — python-harness

The stack half of the shared `standards-reviewer` frame. The frame carries the method and
the reporting rules; this is what "the standards that apply to every change" means here.

A checklist of what to look for, **not the authority**. Where this and `docs/architecture.md`
disagree, the source wins — reread it rather than trusting the summary.

- **Layering** — `api` → `services` → `ai` → `repositories` → `config`. Dependencies point
  one way. A repository importing from `services`, or a route reaching past the service layer
  into a repository, is a violation. So is `ai/` importing a service: services call into
  `ai/`, never the reverse. `ai/evals/` is the documented exception — it may import any layer,
  and nothing imports it.
- **Depend on protocols, not classes** — `Embedder`, `VectorStore` and `Tool` live in
  `repositories/`; implementations are injected. A service constructing a concrete client
  itself is a violation.
- **Pydantic on every I/O surface** — request bodies, responses, tool inputs, config. A dict
  or loose kwargs crossing an external boundary is a violation.
- **Config and secrets only through `app.config.Settings`** — any `os.environ` or `os.getenv`
  outside that module, or a literal key or DSN, is a violation.
- **Async for I/O, plain `def` for CPU and in-memory logic** — an `async def` that never
  awaits, or a blocking call left on the event loop, is a violation. Async buys concurrency,
  not virtue. The `async` axis owns the detail; report the breach and leave it there.
- **structlog with bound context, never `print()`** — and let exceptions surface with their
  cause rather than being swallowed.
- **Type every public function** — parameters and return.

## Where the gate cannot see

`mypy` reads only the paths in `pyproject.toml`'s `files`, and skips dot-directories during
its own discovery. A new top-level directory is unchecked while the gate stays green, so a
typing violation there is a real finding rather than something tooling already owns.
