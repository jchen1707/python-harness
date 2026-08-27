# python-harness

A **harness, not an application**: it defines *how* to build here. Application code goes in
`src/app/` per `docs/architecture.md`. Workload: backend web, RAG, agent orchestration.

## Commands

Everything runs through `uv`. Gates, in the order `/verify` runs them:

```sh
uv run ruff check .        # lint
uv run ruff format --check .
uv run mypy                # disallow_untyped_defs
uv run pytest              # unit only; offline
uv run pytest -m integration   # needs Docker + `uv sync --extra app`
```

`uv sync` installs tooling; `uv sync --extra app` adds the application stack (opt-in, so
the harness stays dependency-free until you build something).

## The workflow

**Ticket-shaped work** runs the main flow, in one unbroken context through `/to-tickets`:

```
/grill-with-docs  →  /to-spec  →  /to-tickets  →  /implement  →  /code-review
```

Alignment work needs continuity; execution work needs a clean slate. Keep steps 1–3 in one
context window — no `/compact`, no `/clear` — so the grilling, spec and tickets build on the
same thinking. Then start each `/implement` **fresh**, working from its ticket and the spec
that ticket names as its parent. Fresh means no conversation history, not no design.

**Every alignment step waits for the user.** `/grill-with-docs` interviews in rounds;
`/to-spec` confirms the **seams** before writing anything (this is the confirmation `/tdd`
requires — it refuses to test at an unconfirmed seam); `/to-tickets` iterates on the
breakdown until the user approves it. Do not run these unattended, and do not treat a
checkpoint as a formality to narrate past.

Alignment settles the *how*, not only the *what*: the spec carries **Implementation
Decisions** (modules, interfaces, architecture, schema, API contracts) and **Testing
Decisions**, both published to the tracker. `/implement` works from the ticket plus that
spec. Add `/plan` on top only when the ticket is large or ambiguous, when the spec's
decisions don't reach into that slice, or when the implementing terminal can't reach the
tracker — not by default.

**Verify the verb and the version before a spec, plan or ticket names a library.**
Confirm the library supports the operation the design asks of it (read vs write, parse
vs render). Confirm the API against the version locked in `pyproject.toml` / `uv.lock`,
not against memory. A wrong claim in a spec is copied into every ticket derived from it.

**Small work** — anything you could describe in one sentence, or a change you want planned
by one model and built by another — uses the repo's own path instead:

```
/plan  →  (new terminal)  →  /implement-from-plan
```

`/plan` writes `plan.md` + `test-plan.md` under `.claude/plans/<branch-slug>/`, gets
explicit sign-off, and stops. `/implement-from-plan` resolves the same directory from
the branch it is on and feeds those files to `/implement` with this repo's gates pinned.
Choose this when the work is too small to spec, or when you want the model-switching handoff.

Either path ends the same way: `/verify`, then `/code-review`, then commit. Committing to a
feature branch and opening a PR needs no permission; committing to `main` does.

### Definition of Done

- All five gate commands above pass
- New behaviour has a test that would fail if the behaviour regressed
- `/code-review` clean on Standards; clean on Spec when there's an originating ticket
- Config and secrets read only through `app.config.Settings`
- Friction worth remembering captured via `/retro`

## What is enforced automatically

CI and pre-commit are the portable enforcement layer. The hooks are **layer A** — one
Node implementation in [`harness`](https://github.com/jchen1707/harness), vendored here
under `.claude/vendor/harness/hooks/` and pinned by sha. They name nothing about this
repo: every path they act on is declared under `hooks` in `harness.config.json`.

| Hook | Effect |
| --- | --- |
| `protect_paths.mjs` (PreToolUse) | Refuses a **write** to `migrations/`, `generated/`, `uv.lock` and the vendored tree; refuses a **read** of `.env` and `.env.*`; refuses the shell commands that reach a secret without naming a file |
| `format_edited.mjs` (PostToolUse) | Runs `ruff format` then `ruff check --fix --unfixable F401` on each edited `.py` |
| `verify.mjs` (Stop) | Blocks the turn while the gates fail — **only** when the turn changed `.py` or `.mjs` under a gated path, or changed a file that defines the gates |
| `session_learnings.mjs` (SessionEnd) | Distils the session's mistakes-and-fixes into a note in the second brain, and rebuilds both vault indexes. Off unless `OBSIDIAN_VAULT_DIRECTORY` is set |

They are JavaScript because a plugin ships one `hooks/` directory and one language had to
win. This repo already ran `full-review.js` with no `package.json` and no `.nvmrc`, so it
gained a *declared* dependency rather than a new one; the frontend repo gained nothing.
`.nvmrc` says 22.

The Stop gate makes a supported session walk-away-able. `HARNESS_SKIP_VERIFY=1` disables it.
The legacy `CLAUDE_SKIP_VERIFY=1` name remains supported.
Claude Code overrides a Stop hook after 8 consecutive blocks; if you hit that, the loop is
stuck on something it cannot fix.

The gated set is *code the gates check, plus the config that defines them* — so prose,
plans and docs still end freely and never burn override budget. Widen it by editing
`hooks.gatedPaths` / `hooks.gatedFiles` in `harness.config.json`;
`tests/test_harness_hooks.py` pins them against literals, so dropping an entry fails the
suite rather than silently going quiet.

## Parallel development

Worktrees are the unit of isolation. Separate checkouts prevent parallel agents from
changing the same files. `.claude/agents/test-writer.md` requests worktree isolation.
Harnesses without frontmatter support must create the worktree before starting the agent.

**A reviewer is half a definition each way.** The shared **frame** — the role, the method,
the reporting rules — is layer A, identical in every stack. What "in this repo's terms" means
is this repo's, at `docs/agents/subagents/<agent-name>.md`. `full-review` concatenates the
two, and the standalone subagent reads the checklist itself, so the two forms cannot drift.

Neither half reviews on its own, and both failures are silent: a frame with no checklist
reviews on general advice and reports a confident clean.

- **Shared frames** — `.claude/vendor/harness/agents/` (the plugin, on `main`). Never edited
  here; edit them in [`harness`](https://github.com/jchen1707/harness) and re-sync.
- **This repo's half** — `docs/agents/subagents/`.
- **This repo's own agents** — `.claude/agents/`: `async-reviewer`, the ninth axis, and
  `test-writer`, which is here because it writes and so its tool grant names a runner.

Harness adapters map tool and model hints to native controls. Treat unsupported frontmatter
fields as advisory.

Add an axis by writing the agent file and naming it in `harness.config.json`; there is no
second copy to keep in step.

**Fork for breadth, stay inline for depth.** Scanning and summarising belong in a subagent;
reasoning you need to steer belongs in the main context. Reviewers get read-only tools by
design — one that can edit will fix things instead of reporting them, and the independent
signal is the whole point.

## Loops and workflows

- **`/loop-goal <goal>`** — standing goals that run until a stop condition holds (docs,
  architecture, logging, tests, deps). Progress lives in `.claude/plans/loop-<goal>.md` so it
  survives compaction.
- **`full-review.js`** — layer A's dynamic workflow, fanning a diff out to nine independent
  reviewers and fanning in to one ranked report. Run it with `/workflows`, or trigger
  workflow mode with the `ultracode` keyword. Reviews against `main` unless `REVIEW_BASE`
  says otherwise (`$env:REVIEW_BASE = "..."`). Nine agents is real spend — reach for
  `/code-review` (two axes) by default and this when the diff warrants it.

  It reads `harness.config.json` for the ninth axis and for which tools already own style,
  and it **throws rather than falling back** when an axis resolves to no frame and no
  checklist. An axis reviewing on a one-line brief reports "no findings" from a reviewer
  that never ran, which is indistinguishable from a clean one.

## Symbol navigation (LSP) — prefer it to grep

`pyright-lsp` runs pyright's language server behind MCP, started from `.mcp.json`. It answers
questions about **symbols**, where grep answers questions about **text**.

Use it when the question is semantic:

| Question | Tool |
| --- | --- |
| Where is this defined? | `definition` |
| What calls this? | `references` |
| What type is this, what does it accept? | `hover` |
| What errors does this file have? | `diagnostics` |
| Rename this symbol everywhere | `rename_symbol` |

Grep matches strings. It cannot tell a definition from a call, a method on the class you
mean from the same name on another class, a real use from a mention in a comment or a
string. On a name like `run`, `get` or `Settings`, grep returns noise and you guess.

**Rule: if you are about to grep for a Python symbol, use the LSP instead.** Keep grep for
what it is good at — text that is not a symbol: config keys, log messages, TODO markers,
strings in Markdown.

The launcher uses `--workspace .`, so it resolves the clone that starts it. It installs
pinned tools in the sandbox cache. Check the server with `/mcp` after session startup.

## Standards

Rules live **next to the code they govern**. Each directory below owns its own
`CLAUDE.md`. Read the one for the directory you are changing.

| Directory | Owns |
| --- | --- |
| `src/app/api/` | HTTP edge, status codes, pagination, `Annotated[T, Depends(...)]` |
| `src/app/core/` | `Settings`, structlog, Prometheus metrics, error types, retries |
| `src/app/repositories/` | SQL, pgvector indexes, protocols, connection pools |
| `src/app/services/` | Orchestration, transaction boundaries, bounded fan-out |
| `src/app/ai/` | Why AI is its own layer; rules covering all of it |
| `src/app/ai/retrieval/` | Chunking, embedding, hybrid search, filtering |
| `src/app/ai/reranking/` | Cross-encoders, fusion, diversity, fallback order |
| `src/app/ai/agents/` | LangGraph, prompt caching, tools, token budgets |
| `src/app/ai/evals/` | Datasets, metric per layer, when to run |
| `tests/` | Unit vs integration, seams, fakes, determinism |

Nested `CLAUDE.md` files are **path-scoped**: working in `api/` does not load
`repositories/CLAUDE.md`. So `docs/architecture.md` keeps only what must hold everywhere —
layering, protocols, types, scaling, extensibility, concurrency, containers, dependency
policy. Load it with `/arch` before non-trivial design work.

The four rules to know without reading anything:

- **Layering**: `api` → `services` → `ai` → `repositories` → `config`. One direction, no
  lateral imports.
- **Depend on protocols**, not classes. Inject implementations at the app factory.
- **Type every public function.** Pydantic on every I/O surface.
- **Unit tests stay offline.** Integration tests use testcontainers.

Pick the architectural style during research, not while coding, and record the choice in
`docs/architecture.md`.

## Reference documentation — read before you write

Load the row that matches the task. Reading the wrong file costs tokens; reading none
costs a rewrite.

| When you are… | Read first |
| --- | --- |
| Adding or changing an endpoint | `src/app/api/CLAUDE.md` |
| Adding config or a secret | `src/app/core/CLAUDE.md` → Configuration |
| Storing an API key, or rotating one | `docs/agents/secrets.md` |
| Adding logging, a metric, or a dashboard | `src/app/core/CLAUDE.md` → Logging, Metrics |
| Designing an error type, retry or timeout | `src/app/core/CLAUDE.md` → Errors, Retries |
| Writing SQL or a migration | `src/app/repositories/CLAUDE.md` |
| Adding a vector index or tuning pgvector | `src/app/repositories/CLAUDE.md` → pgvector |
| Changing chunking, embedding or search | `src/app/ai/retrieval/CLAUDE.md` |
| Changing rank order or fusion | `src/app/ai/reranking/CLAUDE.md` |
| Building or changing an agent graph | `src/app/ai/agents/CLAUDE.md` |
| Touching a prompt, tool, or model choice | `src/app/ai/agents/CLAUDE.md` |
| Measuring whether an AI change helped | `src/app/ai/evals/CLAUDE.md` |
| Starting any AI work at all | `src/app/ai/CLAUDE.md` first |
| Writing any test | `tests/CLAUDE.md` |
| Choosing an architecture or a new library | `docs/architecture.md` |
| Designing for load, or adding an extension point | `docs/architecture.md` → §4, §5 |
| Working with Linear or branch names | `docs/agents/issue-tracker.md` |
| Applying a triage label | `docs/agents/triage-labels.md` |

## Writing style — ASD-STE100

Write every **new** artifact in Simplified Technical English: plans, specs, tickets, pull
request bodies, code comments, docstrings and rule files.

- One instruction per sentence. Keep an instruction under 20 words.
- Use the active voice. Write "the service validates the input", not "the input is
  validated".
- Use one word for one meaning. Do not alternate between "fetch", "get" and "retrieve" for
  the same operation.
- Say what to do, not what to avoid, where both are possible.
- Use the simplest word that is accurate. Technical nouns stay as they are.
- Do not use metaphor, idiom or humour. They do not translate, and an agent reads them
  literally.
- Keep a paragraph to one topic.

This applies to new writing. Existing documents are rewritten only when they are edited
for another reason.

## Stack

`pyproject.toml` fixes application libraries in the `app` extra.
It fixes development tools in the `dev` group. What the file does not explain:

- **Voyage AI** for embeddings because Anthropic has no embeddings API.
- **Postgres + pgvector** over a dedicated vector DB — one datastore, one backup story.
- **LangGraph** for agent orchestration in `ai/agents/`.
- Introducing an alternative to any of these means updating `docs/architecture.md` first.

## Issue tracker

**Linear**, through the Docker MCP Toolkit gateway in `.mcp.json` — check with `/mcp`, where
it shows as *linear*. Workspace **Development**, default team **Backend** (`BAC`). MCP tools
load at session start.
Conventions, tool discovery and wayfinding: `docs/agents/issue-tracker.md`. PRs stay on
GitHub.

Branch as `<type>/<TEAM-NUM>-<slug>` (e.g. `feat/BAC-412-vector-store`) so `/code-review`
can resolve the originating ticket mechanically.

## Environment

- Secrets live in `.env` (gitignored); `.env.example` lists the keys. `app.config.Settings`
  is the only reader. An MCP key goes in the OS credential store under a slot; a harness key
  such as `GH_TOKEN` goes in an OS user environment variable. Where each value belongs, and
  how to store one without exposing it: `docs/agents/secrets.md`.
- A secret that reaches a transcript is compromised. Rotate it; do not estimate the risk.
- `GH_TOKEN` needs `repo` + `workflow` scope for PR automation.
- PowerShell: `$env:VAR = "value"`, backtick continues a line, `;` chains — `&&` does not
  work in 5.1. `uv run` needs no `cd` prefix.

## Where commands come from

- The commands and the shared skills are **layer A**, supplied by the `harness` plugin and
  enabled in `.claude/settings.json`. Every stack fact they need comes from
  `harness.config.json` at the repo root — the gates, the dev server, the review axes.
- `.claude/skills/` holds only this repo's own skills, if any. A shared one appearing there
  is a bug: it would shadow the plugin's.
- `mattpocock/skills` is optional third-party functionality, installed as the
  `mattpocock-skills@claude-plugins-official` plugin.

## Memory

Durable, non-obvious facts go in `~/.claude/projects/<project-slug>/memory/` — one fact per
file, pointer line in `MEMORY.md`. Save decisions, constraints and friction lessons; leave
anything the repo already records to the repo. `/retro` captures a lesson; `/context` audits.

When compacting, preserve the list of modified files and the commands needed to verify them.

### Second brain

A layer above memory, in the user's own notes rather than the agent's:

- **Write** — `session_learnings.mjs` (SessionEnd) distils the session's mistakes and their
  fixes into a dated note under `$OBSIDIAN_VAULT_DIRECTORY/Project Learnings`.
  It splits the note into *Implementation* and *Architecture & design* learnings.
  It writes **nothing** when a session taught nothing.
  SessionEnd fires only on a clean exit — a killed or still-open terminal never distils.
  `node .claude/vendor/harness/hooks/distil_backlog.mjs` recovers those sessions; it lists
  them on a dry run by default and distils with `--run`.
- **One note per session.** `placeNote` keys the note on the session id and reuses the
  note that session already has. A session distils more than once — it is resumed and ends
  again, or the recovery script reaches it while it is still open — and dating each write
  from the clock turned one session into several near-identical notes. The rewrite is not
  lossy: the distiller reads only the last `MAX_TRANSCRIPT_CHARS` of a session, so the
  earlier note goes back into the prompt and its learnings carry forward.
- **The distiller must not read itself.** `distil()` shells out to `claude -p`, and that
  child session writes a transcript holding the prompt *and* the finished note. Distilling
  it returns that note again under a second session id. Two guards: the child runs in
  `DISTILLER_HOME`, outside every repo, so new child transcripts land where nothing scans;
  and `isDistillerTranscript` recognises the ones already on disk, including the ones the
  two predecessor implementations wrote before the guard was one.
- **Audit** — fixing a writer removes nothing it already wrote, so
  `distil_backlog.mjs --audit` reads the vault and reports the notes both bugs left there.
  `--audit --run` deletes the notes written from the distiller's own transcript, which are
  artifacts. It only reports a session holding several notes, because each of those files
  distils a different part of one real session and the merge is a judgement call.
- **Index** — the same hook rebuilds two Markdown indexes, on two different schedules.
  `_VAULT_INDEX.md` at the vault root holds one row per note in the whole vault — path,
  tags, what it covers. It rebuilds on every session end, whether or not a learning was
  written. `Project Learnings/_INDEX.md` holds the session notes, with date and project.
  It rebuilds only when that session wrote a note. `vault_index.mjs` owns
  `_VAULT_INDEX.md`; `session_learnings.mjs` owns `_INDEX.md`. Run `vault_index.mjs`
  standalone to refresh the vault index without ending a session. Both are layer A now, so
  a session ending in **either** harness repo indexes the vault — the lag this section used
  to document is gone.
- **Read** — `/search-second-brain <topic>` reads the indexes, then opens only what
  matches, and reports the pattern across them with citations. Read-only by design.

An Obsidian `.base` file is a **query evaluated by Obsidian's UI**, so reading one returns
the query, never any notes. Bases are for the human; the Markdown indexes are for the
agent. Do not use `LLM.base` for retrieval.

Set `OBSIDIAN_VAULT_DIRECTORY` in **user** settings, never in this repo's committed
`.claude/settings.json`. A clone must not inherit a path to somebody else's vault.
The hooks derive the learnings directory as `<vault>/Project Learnings`.

Three tiers, deliberately: memory is for this project's facts, the second brain is for
transferable lessons across projects, and `CLAUDE.md` / `docs/architecture.md` are for
what has hardened into a rule. A lesson recurring across sessions should be promoted up.
