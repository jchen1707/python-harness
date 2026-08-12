# Adding a secret or an API key

This page covers **where a secret goes and how to put it there**. For the `Settings` field
that reads it, see `src/app/core/CLAUDE.md` → Configuration.

## The rule

A secret is compromised when its value enters an agent transcript. The value is then in the
context window, in the transcript file on disk, and in the request body. No later edit
removes it. Rotation is the only remedy.

Every practice below keeps the literal value out of the model's input. Keeping it out of
git is a separate, already-solved problem.

## Where the value goes

Choose by asking which process reads the value.

| The reader | Store the value in | Example |
| --- | --- | --- |
| `app.config.Settings` (application code) | `.env` at the repo root | `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `POSTGRES_DSN` |
| An MCP server, through `${VAR}` in `.mcp.json` | OS user environment variable | `LINEAR_API_KEY` |
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

## Add a harness or MCP secret

1. Add the `${VAR}` reference to `.mcp.json`. Commit that file. It holds the name, never
   the value.
2. Set the OS user environment variable in an interactive terminal:

   ```powershell
   $k = Read-Host "LINEAR_API_KEY" -AsSecureString
   [Environment]::SetEnvironmentVariable("LINEAR_API_KEY",
     [Runtime.InteropServices.Marshal]::PtrToStringAuto(
       [Runtime.InteropServices.Marshal]::SecureStringToBSTR($k)), "User")
   ```

3. Restart Claude Code. MCP servers read the environment at session start.
4. Confirm the server with `/mcp`.

Use a real terminal for step 2. The `!` prefix runs a command non-interactively, so
`Read-Host` returns an empty value. `SetEnvironmentVariable` then deletes the variable.

Never run `setx VAR "literal"`. That writes the value into shell history.

## Verify without exposing

Check the length or a hash. Never print the value.

```powershell
$env:LINEAR_API_KEY.Length
```

A working MCP call proves only that the value from session start is valid. A long-running
session holds the old value in memory. After a rotation, check the OS variable directly.

## Rotate after any exposure

Treat a value that reached a transcript as compromised. Do not estimate the risk.

1. Revoke the key at the provider.
2. Issue a new key.
3. Store the new value by the procedure above.
4. Restart Claude Code.

## What the harness enforces

These controls hold whatever an instruction says. See `.claude/settings.json` and
`.claude/hooks/`.

| Control | Effect |
| --- | --- |
| `.gitignore` | Excludes `.env` and `.env.*`, and keeps `.env.example` |
| `protect_paths.py` (PreToolUse) | Refuses an agent **write** to `.env` and `.env.*` |
| `permissions.deny` → `Read(./.env)` | Refuses an agent **read** of the secret-bearing files |
| `permissions.deny` → `Bash(cat .env:*)` and similar | Blocks the common shell readers, and `env` / `printenv` |
| `gitleaks` (pre-commit) | Fails a commit that carries a key in any staged file |
| `detect-private-key` (pre-commit) | Fails a commit that carries a private key |

`tests/test_secret_paths.py` pins these rules. Deleting one fails the suite.

Two limits are deliberate, and you should know both.

The Bash deny rules match on a command prefix. `sed -n p .env` still runs. They raise the
cost of an accident; they do not stop intent. The controls that do the real work are
`.gitignore` and the pre-commit scan.

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
