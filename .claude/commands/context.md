---
description: Review context and memory hygiene for this session
---

Assess context/memory management for the current session and report:

1. **Context size**: Is the conversation large? Summarize what's still relevant vs.
   what can be dropped. Propose a compact if warranted.
2. **CLAUDE.md vs memory**: Is anything in CLAUDE.md stale or contradicted by recent
   work? Is anything duplicated between CLAUDE.md and the memory store?
3. **Memory write-back**: Are there durable facts from this session (decisions,
   preferences, non-obvious constraints) that belong in the memory store
   (`C:\Users\jchen\.claude\projects\C--Users-jchen-Documents-python-harness\memory\`)?
   Propose 1–3 concrete memory entries with their `type`
   (user / feedback / project / reference).
4. **Friction write-back**: Did this session hit a bug that took real effort or a
   tool difficulty whose lesson isn't yet captured? If so, suggest `/retro` to record
   it (a `feedback`/`reference` lesson memory) so it doesn't recur.
5. **File hygiene**: Any files re-read unnecessarily, or file state you should trust
   from prior edits rather than re-checking?

Do not write memory or compact without confirmation. Report findings and let the
user decide.