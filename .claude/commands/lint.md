---
description: Lint, format-check, and type-check the project
---

Run all three verification gates and report results:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

If application code under `src/app` exists, ensure the approved app stack is
installed first with `uv sync --extra app`.

Report any violations verbatim with file:line. Fix only what your current change
introduced — do not silently reformat or rewrite unrelated files. Per the
Definition of Done (AGENTS.md), lint + format + types must all be clean before a
change is considered done.