---
description: Review recent changes against the architectural standards
argument-hint: "[PR number/url, or blank for local changes]"
---

Perform a standards-adherence review and **post the findings to the PR** (not just in
this session). `$ARGUMENTS` may name a PR (e.g. `PR #9`, `9`, or a URL); if blank,
target the open PR for the current branch, falling back to local/uncommitted changes.

## 1. Determine the target and the diff
- If `$ARGUMENTS` names a PR, use it. Otherwise run `gh pr view --json number,headRefName,baseRefName`
  to find the open PR for the current branch.
- **PR target**: review the PR's diff — `gh pr diff <number>` or `git diff <base>...HEAD`
  (base from the PR, usually `main`). Note the head SHA (`gh pr view <number> --json headRefName,commits`)
  — inline comments are anchored to it.
- **No PR**: run `git status`, `git diff`, and `git diff --cached` and review local
  changes; skip posting and report in-session (see §5 fallback).

## 2. Load the standards
Read `docs/architecture.md` and the "Architectural standards" + "Definition of Done"
sections of `CLAUDE.md`.

## 3. Check each changed file against the standards
- Correct layer (`api` / `services` / `repositories` / `core` / `config`) and no
  cross-layer leaks or reverse/lateral dependencies.
- Async by default for I/O, sync where simpler; Pydantic models for all external I/O.
- Dependencies behind interfaces/protocols with swappable implementations.
- Config/secrets via `app.config.Settings` — no hardcoded secrets, no scattered env
  reads in logic.
- Public functions typed; `disallow_untyped_defs` satisfied.
- Structlog logging; no `print()`; no swallowed exceptions.
- Tests cover new behavior; no network in unit tests.
- The approved stack is used (FastAPI, LangGraph + langchain-anthropic, Voyage
  embeddings, Postgres + pgvector). New frameworks require updating CLAUDE.md +
  docs/architecture.md first.

Record each finding with `file:line`, the standard it relates to, PASS/FAIL or
observation, and a proposed fix. **Do not apply fixes** — this command only reviews and
comments.

## 4. Post findings to the PR
Submit a single PR review (one API call) carrying both a summary and inline comments:

- **Inline comments** — one per finding that maps to a specific `file:line` that appears
  in the PR diff (added or context lines only; GitHub rejects comments on lines outside
  the diff). Each body states the standard, the issue, and the proposed fix.
- **Summary body** — the per-standard PASS/FAIL checklist plus any findings that have no
  single diff line to anchor to.
- **Event** — `APPROVE` if every standard passes with no FAILs, `REQUEST_CHANGES` if any
  FAIL, else `COMMENT` (passes with only non-blocking observations).

Build the payload and submit with `gh api` (write the JSON to a temp file to avoid
shell-quoting issues):

```bash
# payload.json
# {
#   "body": "<markdown summary + checklist>",
#   "event": "COMMENT",            # or APPROVE / REQUEST_CHANGES
#   "comments": [
#     {"path": "src/app/api/routes/notes.py", "line": 22, "side": "RIGHT",
#      "body": "**§1 layering**: controller imports `Note` from the repository layer..."}
#   ]
# }
gh api --method POST "repos/{owner}/{repo}/pulls/<number>/reviews" --input payload.json
```

Use `repos/{owner}/{repo}` literally — `gh` fills it from the current repo. After
posting, give the user the review URL (`gh pr view <number> --json url`) and a one-line
summary of what was posted. If posting fails (e.g. not authorized, no `gh`), report the
error and fall through to §5.

## 5. Fallback (no PR, or posting unavailable)
Report findings in-session as the per-standard PASS/FAIL checklist with `file:line`
evidence and proposed fixes for any FAILs.
