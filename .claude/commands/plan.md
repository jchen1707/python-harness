---
description: Research + plan a feature as a task list, then write .claude/plans/plan.md for handoff (terminal 1, planning model)
---

Two-terminal workflow — **terminal 1 (planning model)**. Research and plan the work
as a task list, then write an explicit plan file for terminal 2 to implement. Do NOT
write application code here — only research and plan.

The argument is the feature/task to plan: `$ARGUMENTS`.

1. **Build the planning task list** (`TaskCreate`): `Understand` → `Design approach`
   → `Write plan.md`. Work through them in order, marking each in_progress/complete.
2. **Understand** — read the relevant existing code and `docs/architecture.md` (or
   `/arch`). Note the layers, interfaces, and files this work touches.
3. **Design approach** — decide the design (Controller → Service → Repository), where
   each piece lives, which protocols to define/extend, dependencies, risks, and the
   verification steps.
4. **Write the plan** — overwrite `.claude/plans/plan.md` with:
   - **Goal** — what this change delivers.
   - **Context** — findings from step 2 (current state, constraints, files).
   - **Approach** — the design from step 3 (layer placement + interfaces).
   - **Steps** — numbered, concrete, ordered implementation tasks; each names its
     file(s) and layer and is small enough to verify independently. Terminal 2 turns
     this list into its task list.
   - **Verification** — gates to pass (CLAUDE.md Definition of Done: `uv run ruff
     check .`, `ruff format --check .`, `mypy`, `pytest`; `pytest -m integration` if
     DB-backed; then `/review`) and any DB/container setup.
   - **Open questions** — anything terminal 2 should confirm before/while implementing.
5. Mark the planning tasks complete and stop. Tell the user to open terminal 2 and
   run `/implement`.

`plan.md` is gitignored — a local handoff artifact, not committed to git. Plan mode's
own auto-saved file uses a random slug name and isn't a reliable handoff, so this
command writes a stable `plan.md` instead.
