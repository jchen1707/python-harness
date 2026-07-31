# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`docs/architecture.md`** — **the decision record for this repo.** Its "Choosing an
  architecture & design patterns" section records the architectural style and design
  patterns chosen per feature, and the rest is the authoritative standards reference
  (`/arch` loads it). Read it before proposing structural change; treat its recorded
  choices exactly as you would an ADR.
- **`CLAUDE.md`** — the always-loaded summary: approved stack, layering rules,
  Definition of Done. Where it and a skill's generic advice disagree, `CLAUDE.md` wins.
- **`CONTEXT.md`** at the repo root — the domain glossary, if it exists.
- **`docs/adr/`** — individual ADRs, if any exist. This repo has none yet: architectural
  decisions have been recorded in `docs/architecture.md` instead. A per-decision file
  under `docs/adr/` is fine for a decision too narrow to belong in the standards doc,
  but don't migrate the existing record — keep `docs/architecture.md` authoritative.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo (this repo):

```
/
├── CLAUDE.md                  ← standards summary, always loaded
├── CONTEXT.md                 ← domain glossary (not yet created)
├── docs/
│   ├── architecture.md        ← standards + the architectural decision record
│   ├── adr/                   ← optional per-decision files (none yet)
│   └── agents/                ← this file, issue-tracker.md, triage-labels.md
└── src/app/                   ← api/ · services/ · repositories/ (layered)
```

Multi-context layout (a root `CONTEXT-MAP.md` pointing at per-context `CONTEXT.md` files)
does not apply here — this is a single Python package, not a monorepo.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

Note the standing ambiguity this repo has already resolved: **"agent"/"subagent" in
`CLAUDE.md` and these docs means a Claude Code dev-workflow subagent**, not an
application-level LangGraph agent. Application agents are the ones built in
`src/app/services/agents/`. Say which you mean.

## Flag ADR conflicts

If your output contradicts a decision recorded in `docs/architecture.md` (or an ADR under
`docs/adr/`), surface it explicitly rather than silently overriding:

> _Contradicts docs/architecture.md §"Choosing an architecture" (layered + repository) —
> but worth reopening because…_

The layering rule (`api` → `services` → `repositories` → `config`, no reverse deps) and
the approved stack are the two most likely to be contradicted by generic advice. Neither
changes without a `CLAUDE.md` edit first.
