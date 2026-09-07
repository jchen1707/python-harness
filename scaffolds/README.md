# Python project compositions

`components.json` declares stack choices for new projects. Templates supply source files and reviewer checklists.
The shared composer lives in the harness checkout. This catalog owns dependency versions, applicable guidance, and gates.
Existing projects retain their dependencies and architecture until an explicit migration.

## Create a project

Run from this repository. Replace the destination with an empty directory.

```sh
python3 ../harness/scripts/new_project.py compose example-project \
  --catalog scaffolds/components.json --preset fastapi --into /tmp/example-project
```

Use `--preset minimal` for language tooling without an application framework.
Add optional components with repeated `--component <name>` arguments: `postgres`, `rag`, `agents`, and `openai`.
The composer resolves component dependencies and rejects conflicts.
The default adapter vendors layer A. Use `--plugin` for the plugin adapter.
Use `--commit` to create the initial local commit.
Install through the generated config's `install` command. Verify through layer A's gate report.

## Execution contract

Approved tickets start at readiness. Apply the shared ticket-readiness contract from layer A.
Check acceptance criteria, testing seams, dependencies, and current authority.
Use the approved spec or a short execution brief. Interactive planning remains optional.
The builder proves one failing test before implementing each behavior.
Use fresh diagnosis and authority-refresh handoffs when their shared contracts apply.

The generated config records the selected preset and resolved components.
All profiles initially require the declared gates. Projects can record explicit policy deferrals later.
Reviewer frames arrive through layer A. Base templates supply all eight language-specific checklist halves.

## Validate catalog changes

```sh
python3 ../harness/scripts/validate_compositions.py scaffolds/components.json \
  --reports /tmp/python-harness-preset-validation
```

This installs each preset in a temporary project and executes its declared gates.
Consumer tests check that every preset supplies the shared review axes' checklist inputs.
Validate optional components when their manifests change. Keep provider calls offline during validation.
