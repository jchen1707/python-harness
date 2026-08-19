# Second brain — this repo

<!-- harness:agnostic -->

**Shared doctrine lives in `.agents/vendor/harness/skills/search-second-brain/SKILL.md`** —
how to search, what to report, and why there is one indexer rather than one per repository.
It is vendored from [`harness`](https://github.com/jchen1707/harness) and pinned by sha; read
it first.

<!-- /harness:agnostic -->
<!-- harness:claude
**Shared doctrine is provided by the `harness` plugin**, as the `search-second-brain` skill —
how to search, what to report, and why there is one indexer rather than one per repository.
Read it first.
/harness:claude -->

This file records only what is true in **this** repo.

## Both indexes are rebuilt by shared code

`vault_index.mjs` and `session_learnings.mjs` are layer A, vendored under
`.agents/vendor/harness/hooks/`. They rebuild:

| Index                          | Covers                                | Rebuilt                                    |
| ------------------------------ | ------------------------------------- | ------------------------------------------ |
| `_VAULT_INDEX.md` (vault root) | every note in the vault               | every session end with the vault configured |
| `Project Learnings/_INDEX.md`  | the auto-distilled session notes only | only when that session wrote a note         |

This repo used to own both indexes alone, and the cost was a lag: a note written from
`frontend-harness` sat in the folder, unindexed, until a session happened to end here. The
asymmetry was structural — an indexer in both repos would have been one artifact with two
writers, and that pair had already re-diverged once with only one side under test. One
implementation cannot disagree with itself, so both repos run it and the lag is gone.

`distil_backlog.mjs` is the recovery path for sessions that never fired `SessionEnd`, and it
is shared for the same reason: it writes notes through the same code the hook does.

**This is a known asymmetry, not a bug to fix locally.** Adding a second indexer to the other
repo is one artifact with two writers, and it was tried: the pair re-diverged on a header line
inside a single fix cycle. The asymmetry closes when the writer and the indexer move into
layer A — phase 6 — not before.

Never write `_VAULT_INDEX.md` or `_INDEX.md` by hand. They are generated, and a hand edit is
overwritten by the next session that ends here.
