# Second brain — this repo

**Shared doctrine is provided by the `harness` plugin**, as the `search-second-brain` skill —
how to search, what to report, and why there is one indexer rather than one per repository.
Read it first.

This file records only what is true in **this** repo.

## This repo owns both indexes

`vault_index.py` and `distil_backlog.py` run here, at session end, and they rebuild:

| Index                          | Covers                                | Rebuilt                                    |
| ------------------------------ | ------------------------------------- | ------------------------------------------ |
| `_VAULT_INDEX.md` (vault root) | every note in the vault               | every session end with the vault configured |
| `Project Learnings/_INDEX.md`  | the auto-distilled session notes only | only when that session wrote a note         |

So the indexes are current to the last session that ended **here**. Notes written from
`frontend-harness` are in the folder but not in either index until a session ends in this
repo. That is why the shared skill's grep step is not optional.

**This is a known asymmetry, not a bug to fix locally.** Adding a second indexer to the other
repo is one artifact with two writers, and it was tried: the pair re-diverged on a header line
inside a single fix cycle. The asymmetry closes when the writer and the indexer move into
layer A — phase 6 — not before.

Never write `_VAULT_INDEX.md` or `_INDEX.md` by hand. They are generated, and a hand edit is
overwritten by the next session that ends here.
