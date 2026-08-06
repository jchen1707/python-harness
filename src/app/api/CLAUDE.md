# Conventions — `api/`

The HTTP edge. This layer translates between HTTP and the domain. It holds no business
logic.

## Dependency rule

`api` calls `services`. `api` must not import from `repositories` or touch a database
session. If a route needs data, add a service method.

## Rules

- Declare every request body, response body and query model as a Pydantic model. Do not
  return a dict.
- Set `response_model` on every route. This keeps the OpenAPI schema correct.
- Inject dependencies with `Annotated[T, Depends(get_thing)]`. Do not write
  `thing: T = Depends(get_thing)`. Ruff rule B008 rejects the second form.
- Keep route functions short. A route validates input, calls one service method, and
  returns the result.
- Use `async def` for routes that await I/O. Use `def` for routes that do not.
- Raise `HTTPException` only in this layer. Services raise domain errors from
  `core/errors.py`. The exception handler in `core/` maps them to status codes.
- Group routes by resource in `api/routes/<resource>.py`. Register each router in the app
  factory.
- Bind `request_id` to the logger at the start of the request. See `core/CLAUDE.md`.

## Status codes

| Result | Code |
| --- | --- |
| Read succeeded | 200 |
| Resource created | 201 |
| Accepted for async work | 202 |
| Deleted, no body | 204 |
| Input failed validation | 422 (FastAPI default) |
| Caller is not authenticated | 401 |
| Caller is authenticated but not allowed | 403 |
| Resource does not exist | 404 |
| Caller sent too many requests | 429 |

Return 404 rather than 403 when the caller must not learn that a resource exists.

## Pagination

Every list endpoint takes `limit` and `offset`, or a cursor. Set a maximum `limit` and
enforce it in the Pydantic model. An endpoint that returns all rows will fail when the
table grows.

## Tests

Test routes through `httpx.AsyncClient` against the app object. Do not start a server.
Substitute the service with a fake through the dependency override. See `tests/CLAUDE.md`.
