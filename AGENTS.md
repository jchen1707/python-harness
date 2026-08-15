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

`/plan` writes `plan.md` + `test-plan.md` under `.agents/plans/<branch-slug>/`, gets
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

CI and pre-commit are the portable enforcement layer. Harness adapters can run these
shared scripts from `.agents/hooks/`:

| Hook | Effect |
| --- | --- |
| `protect_paths.py` (PreToolUse) | Blocks edits to `.env`, `migrations/`, `generated/`, `uv.lock` |
| `format_edited.py` (PostToolUse) | Runs `ruff format` + `ruff check --fix` on each edited `.py` |
| `verify.py` (Stop) | Blocks the turn while the gates fail — **only** when the turn changed `.py` under `src/`, `tests/` or `.agents/hooks/`, or changed `pyproject.toml` |
| `session_learnings.py` (SessionEnd) | Distils the session's mistakes-and-fixes into a note in the second brain, and rebuilds the vault indexes via `vault_index.py`. Off unless `OBSIDIAN_VAULT_DIRECTORY` is set |

Claude Code calls these scripts directly. Codex adapters accept `apply_patch` payloads and
launch session distillation outside its three-second `SessionEnd` limit.

The Stop gate makes a supported session walk-away-able. `HARNESS_SKIP_VERIFY=1` disables it.
The legacy `CLAUDE_SKIP_VERIFY=1` name remains supported.
Claude Code overrides a Stop hook after 8 consecutive blocks. Codex continues until the
gate passes or the user interrupts it.

The gated set is *code the gates check, plus the config that defines them* — so prose,
plans and docs still end freely and never burn override budget. Widen it by editing
`GATED_PATHS` / `GATED_FILES` in `verify.py`; `tests/test_verify_hook.py` pins the
pathspec, so dropping an entry fails the suite rather than silently going quiet.

## Parallel development

Worktrees are the unit of isolation. Separate checkouts prevent parallel agents from
changing the same files. `.agents/agents/test-writer.md` requests worktree isolation.
Harnesses without frontmatter support must create the worktree before starting the agent.

Subagent prompts live in `.agents/agents/`. Harness adapters map their tool and model hints
to native controls. Treat unsupported frontmatter fields as advisory.

The nine reviewers are also the nine axes of `full-review.js`, which reads each prompt from
the agent file rather than restating it. Add an axis by writing the agent file and adding
one entry to `AXES`; there is no second copy to keep in step.

**Fork for breadth, stay inline for depth.** Scanning and summarising belong in a subagent;
reasoning you need to steer belongs in the main context. Reviewers get read-only tools by
design — one that can edit will fix things instead of reporting them, and the independent
signal is the whole point.

## Loops and workflows

- **`/loop-goal <goal>`** — standing goals that run until a stop condition holds (docs,
  architecture, logging, tests, deps). Progress lives in `.agents/plans/loop-<goal>.md` so it
  survives compaction.
- **`.agents/workflows/full-review.js`** — dynamic workflow fanning a diff out to nine
  independent reviewers and fanning in to one ranked report. Run it with `/workflows`, or
  trigger workflow mode with the `ultracode` keyword. Reviews against `main` unless
  `REVIEW_BASE` says otherwise (`$env:REVIEW_BASE = "..."`). Nine agents is real spend —
  reach for `/code-review` (two axes) by default and this when the diff warrants it.
- **`/full-review`** — portable skill that runs the same fan-out and fan-in through native
  subagents. It uses each harness adapter under `.agents/agents/` and `.codex/agents/`.

## Symbol navigation (LSP) — prefer it to grep

`pyright-lsp` in `.mcp.json` runs pyright's language server behind MCP. It answers
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

The server is declared with `--workspace .`, so it resolves to whatever clone it starts
in. Check it with `/mcp`. MCP servers load at session start, so a fresh install needs a
restart. One-time machine setup is in the README.

## Standards

Rules live **next to the code they govern**. Each directory below owns its own
`AGENTS.md`. Read the one for the directory you are changing.

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

Nested `AGENTS.md` files are **path-scoped**: working in `api/` does not load
`repositories/AGENTS.md`. So `docs/architecture.md` keeps only what must hold everywhere —
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
| Adding or changing an endpoint | `src/app/api/AGENTS.md` |
| Adding config or a secret | `src/app/core/AGENTS.md` → Configuration |
| Storing an API key, or rotating one | `docs/agents/secrets.md` |
| Adding logging, a metric, or a dashboard | `src/app/core/AGENTS.md` → Logging, Metrics |
| Designing an error type, retry or timeout | `src/app/core/AGENTS.md` → Errors, Retries |
| Writing SQL or a migration | `src/app/repositories/AGENTS.md` |
| Adding a vector index or tuning pgvector | `src/app/repositories/AGENTS.md` → pgvector |
| Changing chunking, embedding or search | `src/app/ai/retrieval/AGENTS.md` |
| Changing rank order or fusion | `src/app/ai/reranking/AGENTS.md` |
| Building or changing an agent graph | `src/app/ai/agents/AGENTS.md` |
| Touching a prompt, tool, or model choice | `src/app/ai/agents/AGENTS.md` |
| Measuring whether an AI change helped | `src/app/ai/evals/AGENTS.md` |
| Starting any AI work at all | `src/app/ai/AGENTS.md` first |
| Writing any test | `tests/AGENTS.md` |
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

Fixed in `pyproject.toml` (`app` extra) — read it there. What the file doesn't explain:

- **Voyage AI** for embeddings because Anthropic has no embeddings API.
- **Postgres + pgvector** over a dedicated vector DB — one datastore, one backup story.
- **LangGraph** for agent orchestration in `ai/agents/`.
- Introducing an alternative to any of these means updating `docs/architecture.md` first.

## Issue tracker

**Linear**, as a project MCP server in `.mcp.json` — check with `/mcp`, where it shows as
*linear*. Workspace **Development**, default team **Backend** (`BAC`). It authenticates
with an API key. `.mcp.json` carries only a `headersHelper` line naming the credential slot
`linear-py`, and both it and `.claude/settings.json` are committed. MCP tools load at
session start, so storing the key mid-session needs a restart. Conventions, tool discovery
and wayfinding: `docs/agents/issue-tracker.md`. PRs stay on GitHub.

**The key lives in the OS credential store, never in an environment variable.**
`.agents/mcp_headers.py` reads the slot at connection time and writes the header to stdout,
which Claude Code consumes itself. A `${VAR}` header would put the key in every Bash
subprocess, where one careless `echo` compromises it. Storing, verifying and rotating:
`docs/agents/secrets.md`.

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

- `.agents/skills/` is the canonical repo-owned skill directory. Claude Code reaches it
  through `.claude/skills`. Harnesses may use native invocation instead of slash commands.
- `.claude/commands/` contains Claude wrappers. Matching skills in `.agents/skills/` make
  each repository command available to Codex.
- `mattpocock/skills` is optional third-party functionality. Install it through the active
  harness's plugin or skill installer. Never assume a Claude plugin exists in Codex.

## Memory

Durable, non-obvious facts go in `~/.claude/projects/<project-slug>/memory/` — one fact per
file, pointer line in `MEMORY.md`. Save decisions, constraints and friction lessons; leave
anything the repo already records to the repo. `/retro` captures a lesson; `/context` audits.

When compacting, preserve the list of modified files and the commands needed to verify them.

### Second brain

A layer above memory, in the user's own notes rather than the agent's:

- **Write** — `session_learnings.py` (SessionEnd) distils the session's mistakes and their
  fixes into a dated note under `$OBSIDIAN_VAULT_DIRECTORY/Project Learnings`.
  It splits the note into *Implementation* and *Architecture & design* learnings.
  It writes **nothing** when a session taught nothing.
  SessionEnd fires only on a clean exit — a killed or still-open terminal never distils.
  `distil_backlog.py` recovers those sessions; it lists them on a dry run by default and
  distils with `--run`.
- **One note per session.** `note_path` keys the filename on the session id and reuses the
  note that session already has. A session distils more than once — it is resumed and ends
  again, or the recovery script reaches it while it is still open — and dating each write
  from the clock turned one session into several near-identical notes. The rewrite is not
  lossy: the distiller reads only the last `MAX_TRANSCRIPT_CHARS` of a session, so the
  earlier note goes back into the prompt and its learnings carry forward.
- **The distiller must not read itself.** `distil()` shells out to `claude -p`, and that
  child session writes a transcript holding the prompt *and* the finished note. Distilling
  it returns that note again under a second session id. Two guards: the child runs in
  `DISTILLER_HOME`, outside every repo, so new child transcripts land where nothing scans;
  and `is_distiller_transcript` recognises the ones already on disk.
- **Audit** — fixing a writer removes nothing it already wrote, so
  `distil_backlog.py --audit` reads the vault and reports the notes both bugs left there.
  `--audit --run` deletes the notes written from the distiller's own transcript, which are
  artifacts. It only reports a session holding several notes, because each of those files
  distils a different part of one real session and the merge is a judgement call.
- **Index** — the same hook rebuilds two Markdown indexes, on two different schedules.
  `_VAULT_INDEX.md` at the vault root holds one row per note in the whole vault — path,
  tags, what it covers. It rebuilds on every session end, whether or not a learning was
  written. `Project Learnings/_INDEX.md` holds the session notes, with date and project.
  It rebuilds only when that session wrote a note. `vault_index.py` owns
  `_VAULT_INDEX.md`; `session_learnings.py` owns `_INDEX.md`. Run `vault_index.py`
  standalone to refresh the vault index without ending a session.
- **Read** — `/search-second-brain <topic>` reads the indexes, then opens only what
  matches, and reports the pattern across them with citations. Read-only by design.

An Obsidian `.base` file is a **query evaluated by Obsidian's UI**, so reading one returns
the query, never any notes. Bases are for the human; the Markdown indexes are for the
agent. Do not use `LLM.base` for retrieval.

Set `OBSIDIAN_VAULT_DIRECTORY` in **user** settings, never in this repo's committed
`.claude/settings.json`. A clone must not inherit a path to somebody else's vault.
The hooks derive the learnings directory as `<vault>/Project Learnings`.

Three tiers, deliberately: memory is for this project's facts, the second brain is for
transferable lessons across projects, and `AGENTS.md` / `docs/architecture.md` are for
what has hardened into a rule. A lesson recurring across sessions should be promoted up.
