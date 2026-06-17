---
description: Research + plan a feature (implementation plan + test plan), get user sign-off, then STOP for handoff (terminal 1, planning model)
---

Two-terminal workflow — **terminal 1 (planning model)**. Research and plan the work,
write an **implementation plan** and a **test plan**, get the user's explicit sign-off,
then **STOP**. Do NOT write application code or implement here — planning only.

The argument is the feature/task to plan: `$ARGUMENTS`.

1. **Build the planning task list** (`TaskCreate`): `Understand` → `Design approach` →
   `Write plan.md` → `Write test-plan.md` → `Get user sign-off`. Work through them in
   order, marking each in_progress/complete.
2. **Understand** — read the relevant existing code and `docs/architecture.md` (or
   `/arch`). Note the layers, interfaces, and files this work touches.
3. **Design approach** — decide the design (Controller → Service → Repository), where
   each piece lives, which protocols to define/extend, dependencies, risks, and the
   verification steps.
4. **Write the implementation plan** — overwrite `.claude/plans/plan.md` with:
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
5. **Write the test plan** — overwrite `.claude/plans/test-plan.md` with:
   - **Scope** — the behaviors that must be covered (tie each back to a plan Step).
   - **Unit tests (offline)** — the cases per layer (repository / service / api), and the
     fakes/stubs to use (`FakeEmbedder`, in-memory store, stubbed `ChatAnthropic`). No
     network/DB — these are the default `uv run pytest` run.
   - **Integration tests** — any testcontainers/pgvector cases (marked `integration`),
     with the seed/reset they rely on; or "none" with a one-line reason.
   - **Edge cases & failure modes** — validation errors, not-found, limits/bounds,
     cancellation/concurrency, empty inputs.
   - **How to run** — the exact commands and which Definition-of-Done gates this covers.
6. **Get user sign-off (REQUIRED checkpoint — do not skip).** Present a concise summary
   of both `plan.md` and `test-plan.md` and explicitly ask the user to confirm they look
   correct, using `AskUserQuestion` (e.g. "Approve plan & test plan / Revise"). Revise
   and re-ask until the user approves. Do NOT proceed past this checkpoint on your own —
   even in autonomous/auto mode, planning requires this explicit user verification.
7. **STOP — do not implement.** After sign-off, mark the planning tasks complete and
   stop. Tell the user to open terminal 2 (implementation model) and run `/implement`.
   Implementing is a separate, explicit step — never roll straight from planning into
   writing code, even in a single terminal.

`plan.md` and `test-plan.md` are gitignored — local handoff artifacts, not committed to
git. Plan mode's own auto-saved file uses a random slug name and isn't a reliable
handoff, so this command writes the stable `plan.md` / `test-plan.md` instead.
