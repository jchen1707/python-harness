# Out-of-Scope

Persistent records of **rejected** feature requests. `/triage` reads every file here during
step 1 (gather context) to check whether a new request was already turned down, so a
rejection doesn't get re-litigated from scratch each time it resurfaces.

## Rules

- **One file per concept, not per issue.** Three issues asking for the same thing share one
  file and accumulate in its "Prior requests" list.
- **Kebab-case concept names**: `dark-mode.md`, `plugin-system.md`, `graphql-api.md`.
  Recognisable without opening the file.
- **Only rejected enhancements land here.** Not bugs, and *not* things closed as `wontfix`
  because they're already implemented — recording those would poison the dedup check with
  false rejections. A built feature gets a closing comment pointing at where it lives.
- **Reasons must be durable.** Scope, philosophy, or a technical constraint — not "we're
  busy right now", which is a deferral, not a rejection.

## File format

```markdown
# Dark Mode

This project does not support dark mode or user-facing theming.

## Why this is out of scope

The rendering pipeline assumes a single palette defined in `ThemeConfig`. Supporting
multiple themes would require a theme context provider, per-component style resolution,
and a persistence layer for the preference — a significant architectural change that
doesn't align with the project's focus on content authoring.

## Prior requests

- ENG-42 — "Add dark mode support"
- ENG-87 — "Night theme for accessibility"
```

Use Linear identifiers (`ENG-42`), not bare integers — see `docs/agents/issue-tracker.md`.

Full spec: `skills/engineering/triage/OUT-OF-SCOPE.md` in the `mattpocock-skills` plugin.
