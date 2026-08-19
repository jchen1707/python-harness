# Security checklist — python-harness

The stack half of the shared `security-reviewer` frame. The frame carries the method — trace
the data, give the attack path, confirm reachability — and the reporting rules. This is what
to prioritise here.

The stack is FastAPI + Pydantic v2 + Postgres/pgvector + LangGraph; `docs/architecture.md` is
the authority.

- **Secrets** — anything read from the environment outside `app.config.Settings`, any literal
  key, token or DSN, any secret reaching logs or an exception message.
- **Injection** — raw SQL or f-string-built queries instead of parameters; command injection
  via `subprocess` or `os.system`; prompt injection where retrieved documents or user text
  are concatenated into an LLM system prompt.
- **Input validation** — request bodies, query params and tool inputs that bypass a Pydantic
  model; missing bounds on limits, offsets and vector `k`.
- **AuthN/AuthZ** — endpoints missing a dependency that enforces identity; object-level checks
  absent, so one user can read another's rows.
- **Unsafe deserialization** — `pickle`, `yaml.load` without `SafeLoader`, `eval`.
- **Async and resource issues with a security impact** — unbounded concurrency enabling
  amplification, missing timeouts on outbound `httpx` calls.
- **Dependency risk** — packages added outside the approved stack in `AGENTS.md`.

## Read-only means read-only

This agent has no `Bash(uv run:*)` grant, and should not be given one. Its own doctrine is
"report, never fix"; a grant that can install, run and write contradicts it, and the
contradiction is invisible until something acts on it.
