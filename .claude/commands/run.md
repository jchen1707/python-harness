---
description: Start the FastAPI dev server (uvicorn --reload)
---

Start the FastAPI development server in the background:

```sh
uv run uvicorn app.main:create_app --factory --reload
```

Requirements (per docs/architecture.md):
- The approved app stack must be installed: `uv sync --extra app`.
- `src/app/main.py` must exist and expose a `create_app` factory (a callable that
  returns a FastAPI app). There is no module-level `app`, so importing `app.main` does
  not read the environment.

If `src/app/main.py` does not yet exist, tell the user the application entry point
hasn't been implemented and stop — do not create it yourself unless asked. Once
running, report the URL (http://127.0.0.1:8000) and confirm `/healthz` responds.