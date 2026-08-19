# Adding a secret or an API key — this repo

**Shared doctrine is provided by the `harness` plugin**, at
`${CLAUDE_PLUGIN_ROOT}/docs/agents/secrets.md` — why a pasted value is already burned, how to
add one, and what to do when one leaks. Read it first.

This page covers **where a secret goes in this repo and how to put it there**. For the
`Settings` field that reads it, see `src/app/core/CLAUDE.md` → Configuration.

## Where the value goes

Choose by asking which process reads the value.

| The reader | Store the value in | Example |
| --- | --- | --- |
| `app.config.Settings` (application code) | `.env` at the repo root | `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `POSTGRES_DSN` |
| A Docker MCP server | Docker Desktop's credential store | Linear |
| A hook, or the `gh` CLI | OS user environment variable | `GH_TOKEN` |

Never store a secret in `~/.claude/settings.json` → `env`, in `.claude/settings.json`, in
source code, or in a plan file.

`~/.claude/settings.json` deserves the specific warning. It keeps the value out of git, so
it looks safe. It is plain text that an agent reads for unrelated reasons — to check
`enabledPlugins`, or a hook path. One whole-file read copies the key into the transcript.
An OS user variable is in no file the agent reads.

## Add an application secret

1. Add the key to `.env.example` with an empty value. Commit that file.
2. Add the field to `app.config.Settings`. `Settings` is the only reader of the environment.
3. Create `.env` if it does not exist. `.gitignore` already excludes it.
4. Put the real value in `.env` yourself, in your editor or a terminal.

Ask the agent to do steps 1 and 2. Do step 4 yourself.

## Add a Docker MCP secret

Docker Desktop owns credentials for servers supplied through Docker MCP Toolkit.

1. Select the required Docker Desktop MCP Toolkit profile.
2. Enable the server in that profile.
3. Authenticate the server through Docker Desktop.
4. Restart the agent client.
5. Confirm the server with `/mcp`.

Do not copy the credential into `.mcp.json` or an environment variable.

## Add a harness secret

A hook or the `gh` CLI reads its own environment, so those values stay in OS user
variables. `GH_TOKEN` is the live example.

```powershell
$k = Read-Host "GH_TOKEN" -AsSecureString
[Environment]::SetEnvironmentVariable("GH_TOKEN",
  [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($k)), "User")
```

Use a real terminal here too. Under `!`, `Read-Host` returns empty and
`SetEnvironmentVariable` then deletes the variable.

## Verify without exposing

Check the exit code, a length or a hash. Never print the value.

```powershell
$env:GH_TOKEN.Length
```

A working MCP call proves only that the credential was valid when the connection opened.
A long-running session holds the value it read at start. After a rotation, check the store
directly and restart.

## Rotate after any exposure

Treat a value that reached a transcript as compromised. Do not estimate the risk.

1. Revoke the key at the provider.
2. Issue a new key.
3. Store the new value through Docker Desktop or the documented reader.
4. Restart the agent client.

## What the harness enforces

These controls hold whatever an instruction says. See `.claude/settings.json`,
`harness.config.json` and `.claude/vendor/harness/hooks/`.

| Control | Effect |
| --- | --- |
| `.gitignore` | Excludes `.env` and `.env.*`, and keeps `.env.example` |
| `protect_paths.mjs` (PreToolUse) | Refuses an agent **write** to `.env` and `.env.*` |
| `permissions.deny` → `Read(./.env)` | Refuses an agent **read** of the secret-bearing files |
| `permissions.deny` → `Bash(cat .env:*)` and similar | Blocks the common shell readers of the file |
| `permissions.deny` → `Bash(env)`, `Bash(set)`, `Bash(Get-ChildItem Env:*)` and similar | Blocks a whole-environment dump in both shells |
| `permissions.deny` → `Bash(echo $LINEAR_API_KEY:*)` and similar | Blocks the common spellings that read one variable |
| `permissions.deny` → `Bash(python -c:*)`, `Bash(node -e:*)` and similar | Blocks an inline interpreter, which reads the environment without naming the variable |
| `PreToolUse` on `Read\|Bash` → `protect_paths.mjs` | Refuses an agent **read** of a secret file, and blocks the environment dumps, single-variable expansions and interpreter one-liners a literal deny pattern cannot name |
| `gitleaks` (pre-commit) | Fails a commit that carries a key in any staged file |
| `detect-private-key` (pre-commit) | Fails a commit that carries a private key |

`tests/test_harness_hooks.py` pins the deny rules, the variable names the hook watches, and
the wiring that decides which tool calls the guard ever sees; `tests/test_mcp_headers.py`
pins the helper. Deleting one fails the suite.

The `.env` rules are **not** in `harness.config.json`. `protect_paths.mjs` carries them as a
built-in floor that no config can lower, because a guard whose config goes missing and
quietly protects nothing is worse than no guard — the repo still reads as protected.

Three limits are deliberate, and you should know all three.

The Bash deny rules match on a command prefix. `sed -n p .env` still runs. They raise the
cost of an accident; they do not stop intent. The controls that do the real work are
`.gitignore` and the pre-commit scan.

An OS user variable has a weaker ceiling than a file. Claude Code inherits it, and every
Bash subprocess inherits it in turn. A prefix rule cannot cover every spelling of a shell
expansion: `echo $VAR`, `echo "$VAR"` and `printf %s "$VAR"` are three commands, and
indirection defeats all three. The rules above name the careless spellings. Treat them as
a speed bump. Keep service credentials out of the environment when the service supports a
credential store. `GH_TOKEN` still lives in a variable because the `gh` CLI reads its
environment.

The deny rules bind this repository only. `.claude/settings.json` is per project, and the
same OS user variable reaches every other clone on the machine. Mirror these rules into
`~/.claude/settings.json` to cover a session started anywhere else.

The read rules name each `.env` variant instead of globbing `.env.*`. A glob would also
deny `.env.example`, which is committed and holds no values. Add a new variant to both
`.claude/settings.json` and `tests/test_secret_paths.py` when you start using one.

## Working near a secret

Ask the agent to read a filtered view, rather than pasting a block that contains a key.
Name the file and what to check. A log line, a failing request or a config file often
carries a token beside the part you care about.

When a file is known to hold a literal, change it programmatically. A short script that
reads, edits and reports only key names gives the same result with no exposure. Reading the
whole file to change one unrelated key is what exposes the rest.
