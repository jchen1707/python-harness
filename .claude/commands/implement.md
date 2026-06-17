---
description: Read .claude/plans/plan.md, build a fresh task list from it, and implement to the Definition of Done (terminal 2, implementation model)
---

Two-terminal workflow — **terminal 2 (implementation model)**. Read the plan written
by terminal 1, build a fresh task list from it, and implement the rest. Do not re-plan
from scratch — the plan is the source of truth; only flag issues back.

1. **Read the plan** — read `.claude/plans/plan.md` (or the path in `$ARGUMENTS` if
   given). If it's missing, stop and tell the user to run `/plan` in terminal 1 first.
2. **Build the implementation task list** — create one `TaskCreate` task per numbered
   **Step** in the plan (plus a final `Verify` task). Work them in order, marking each
   in_progress/complete.
3. **Implement** — for each step, write code in the correct layer (`api` / `services`
   / `repositories` / `config`), types on every public function, Pydantic for I/O,
   async for I/O, dependencies behind interfaces. No `print()` (use structlog); no
   hardcoded secrets.
4. **Verify** — run the gates per the plan's Verification section and CLAUDE.md
   Definition of Done: `/lint`, then `/test` (then `uv run pytest -m integration` for
   DB-backed work), then `/review`. Fix root causes; don't paper over failures.
5. **Update the plan** — as you complete steps, update `.claude/plans/plan.md` (mark
   steps done, note deviations or follow-ups) so the plan reflects reality.
6. **Commit** — only when asked; keep changes minimal and per-layer. Ship substantive
   changes via a PR, not a direct commit to `main`.

`plan.md` is gitignored — it's a local working artifact, not committed.
