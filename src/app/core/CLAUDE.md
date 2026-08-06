# Conventions — `core/`

Cross-cutting concerns: configuration, logging, metrics, error types and middleware.

## Dependency rule

`core` imports nothing from `api`, `services` or `repositories`. Every other layer may
import `core`. A `core` module that imports a service creates a cycle.

## Configuration

`config.py` holds one `Settings` class, built on `pydantic-settings`.

- `Settings` is the only reader of the environment and of `.env`. No other module calls
  `os.getenv`.
- Give each field a type and, where safe, a default. Fail at startup when a required
  secret is absent. Do not fail at first use.
- Use `SecretStr` for keys and passwords. This keeps them out of logs and tracebacks.
- Build `Settings` once and inject it. Do not construct it inside a function.

## Logging

`logging.py` configures `structlog` once. The app factory calls it.

- Emit JSON in production and human-readable output in development.
- Bind context, do not format strings. Write `log.info("user.created", user_id=id)`. Do
  not write `log.info(f"created user {id}")`. Bound keys are searchable; formatted strings
  are not.
- Bind `request_id` at the edge. `structlog` reads `contextvars`, so every later log line
  in that request carries it.
- Never call `print()`.
- Never log a secret, a token, a full request body, or personal data.
- Name events as `noun.verb` in the past tense: `document.indexed`, `query.rejected`.

## Metrics

`metrics.py` exposes Prometheus metrics. Grafana reads them.

- Instrument every service with the **RED** method: **R**ate, **E**rrors, **D**uration.
  Instrument every resource with the **USE** method: **U**tilisation, **S**aturation,
  **E**rrors.
- Use a `Counter` for totals, a `Histogram` for latency and a `Gauge` for a level that
  goes up and down. Do not use a `Summary`; it cannot be aggregated across instances.
- Set histogram buckets to match the target latency. The default buckets are wrong for
  most services.
- Keep label cardinality low. Never use a user id, a request id, a raw query or a URL path
  with an id in it as a label value. High cardinality will exhaust Prometheus memory.
- Name metrics `<namespace>_<subsystem>_<unit>` and end the name with the unit, for
  example `app_http_request_duration_seconds`. Use seconds, not milliseconds.
- Serve `/metrics` from the app. Exclude it from access logs and from authentication.

Metrics measure. Logs explain. Record the count in a metric and the reason in a log.

## Errors

`errors.py` defines the domain error types.

- Define one base error for the application. Derive a small number of specific errors from
  it, for example `NotFoundError`, `ConflictError`, `ValidationError`,
  `DependencyError`.
- A service raises a domain error. Only `api/` converts it to an HTTP status code.
- Never write `except: pass`. Never write `except Exception: pass`.
- Re-raise with context: `raise DependencyError("voyage embed failed") from exc`. The
  `from` clause keeps the original traceback.
- Catch the narrowest exception that can occur. A broad `except Exception` hides defects.

## Retries and timeouts

- Set an explicit timeout on every outbound call. A call with no timeout can hold a
  connection until the process restarts.
- Retry only errors that can succeed on a second attempt: a timeout, a 429, or a 5xx. Do
  not retry a 4xx.
- Use exponential backoff with jitter. Set a maximum number of attempts.
- Make a retried operation idempotent, or give it an idempotency key.
