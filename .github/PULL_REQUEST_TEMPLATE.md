<!-- A PR with an empty body is not done (AGENTS.md, Definition of Done). Fill every
section. Write in Simplified Technical English. -->

## Summary

<!-- One paragraph: what this PR delivers and why. Include the magic words
"Fixes BAC-123" on their own line — Linear's GitHub integration reads them to move the
issue to In Review on open and Done on merge. -->

## What changed

<!-- The changes a reviewer must know about, grouped by area. Not a file list — git has
that. Name the decisions: new slice, new interface, promoted component, changed contract. -->

## How to demo

<!-- Exact commands and the route to open. The reviewer must not guess.
Example:
```sh
uv run uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000/healthz -->

## Evidence

<!-- Paste the real gate results, not an assertion that they passed:
ruff check, ruff format --check, mypy, pytest; pytest -m integration when a change reaches
Postgres or pgvector. Name any gate that did not run, with the reason. -->

## Risks and follow-ups

<!-- What could break, what is deliberately out of scope, and the ticket that owns it. -->