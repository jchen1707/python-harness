# Domain Docs — this repo

**Shared doctrine is provided by the `harness` plugin**, at
`${CLAUDE_PLUGIN_ROOT}/docs/agents/domain.md` — what to read before exploring, the
proceed-silently rule, the glossary-vocabulary rule and how to flag an ADR conflict. Read it
first.

This file records only what is true in **this** repo.

## File structure

```
/
├── CLAUDE.md                  ← standards summary, always loaded
├── docs/
│   ├── architecture.md        ← standards + the architectural decision record
│   ├── adr/                   ← optional per-decision files (none yet)
│   └── agents/                ← this file, issue-tracker.md, triage-labels.md
└── src/app/                   ← api/ · services/ · ai/ · repositories/ · core/ (layered,
                                  each with its own CLAUDE.md)
```

A single Python package, not a monorepo — the multi-context `CONTEXT-MAP.md` layout does not
apply.

`docs/architecture.md`'s "Choosing an architecture & design patterns" section is the
per-feature decision record here.

## Vocabulary this repo has settled

- **"agent"/"subagent" means a dev-workflow subagent**, not an application-level LangGraph
  agent. The application's own agents are the ones built in `src/app/ai/agents/`. Say which
  you mean.

## The rule most likely to be contradicted

The layering rule — `api` → `services` → `ai` → `repositories` → `config`, no reverse
dependencies — and the approved stack. Neither changes without an `CLAUDE.md` edit first.

> _Contradicts docs/architecture.md §"Choosing an architecture" (layered + repository) — but
> worth reopening because…_
