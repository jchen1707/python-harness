---
description: Run the test suite (uv run pytest) and report results
---

Run the project test suite and report results:

```sh
uv run pytest
```

If application code under `src/app` exists, ensure the approved app stack is
installed first with `uv sync --extra app`.

Report the pass/fail summary and any failures verbatim (with file:line). **Do not
modify tests or source to make failing tests pass** — diagnose the root cause and
propose a fix instead. Per the Definition of Done (CLAUDE.md), tests must be green
before a change is considered done.