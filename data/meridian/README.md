# Meridian mock corpus

`documents.json` contains the text for 20 fictional Meridian documents.
Each document contains shared context and four page-specific text fields.
The generator puts the shared context before each page-specific field.

`gold_set.json` contains 20 natural support queries.
An `expected_document_id` value identifies the one correct document.
A null value marks a query that has no answer in the corpus.

Install the application extra because the generator validates JSON with Pydantic:

```sh
uv sync --extra app
```

Then run this command from the repository root:

```sh
uv run python scripts/generate_meridian_corpus.py
```

The command writes PDFs to `artifacts/meridian-corpus/`.
Git ignores this directory.
