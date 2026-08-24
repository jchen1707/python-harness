"""Behaviour tests for the committed Meridian corpus and PDF generator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "meridian"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
GOLD_SET_PATH = DATA_DIR / "gold_set.json"
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_meridian_corpus.py"
EXPECTED_GOLD_LABELS = {
    "gold-01": "external-sign-in",
    "gold-02": "external-sign-in",
    "gold-03": "external-profile-security",
    "gold-04": "external-billing",
    "gold-05": "external-billing",
    "gold-06": "external-plans-seats",
    "gold-07": "external-plans-seats",
    "gold-08": "external-quotas",
    "gold-09": "external-exports",
    "gold-10": "external-schedules",
    "gold-11": "external-api-auth",
    "gold-12": "external-api-auth",
    "gold-13": "external-api-errors",
    "gold-14": "external-webhooks",
    "gold-15": "external-webhooks",
    "gold-16": "internal-refunds",
    "gold-17": "internal-account-recovery",
    "gold-18": "internal-rate-overrides",
    "gold-19": None,
    "gold-20": None,
}


@pytest.fixture(scope="module")
def documents() -> dict[str, Any]:
    """Load the committed document source."""
    return json.loads(DOCUMENTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gold_set() -> dict[str, Any]:
    """Load the committed retrieval labels."""
    return json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def generator() -> ModuleType:
    """Load the command module through its documented file path."""
    spec = importlib.util.spec_from_file_location("_meridian_generator_under_test", GENERATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_document_source_has_the_approved_shape(documents: dict[str, Any]) -> None:
    """The committed corpus has the requested size, visibility split, and page lengths."""
    corpus = documents["documents"]
    assert len(corpus) == 20
    assert {document["visibility"] for document in corpus} == {"external", "internal"}
    assert sum(document["visibility"] == "external" for document in corpus) == 10
    assert sum(document["visibility"] == "internal" for document in corpus) == 10
    assert len({document["id"] for document in corpus}) == 20
    assert len({document["file_name"] for document in corpus}) == 20

    for document in corpus:
        assert 4 <= len(document["pages"]) <= 6
        for page in document["pages"]:
            rendered_page = f"{document['context']} {page}"
            assert 200 <= len(rendered_page.split()) <= 300


def test_gold_set_has_the_approved_answer_categories(
    documents: dict[str, Any], gold_set: dict[str, Any]
) -> None:
    """Gold labels include 15 external, three internal, and two unanswered queries."""
    visibility_by_id = {
        document["id"]: document["visibility"] for document in documents["documents"]
    }
    queries = gold_set["queries"]
    expected_ids = [query["expected_document_id"] for query in queries]

    assert len(queries) == 20
    assert len({query["id"] for query in queries}) == 20
    assert sum(expected_id is None for expected_id in expected_ids) == 2
    assert (
        sum(
            expected_id is not None and visibility_by_id[expected_id] == "external"
            for expected_id in expected_ids
        )
        == 15
    )
    assert (
        sum(
            expected_id is not None and visibility_by_id[expected_id] == "internal"
            for expected_id in expected_ids
        )
        == 3
    )


def test_gold_query_labels_match_the_approved_answers(gold_set: dict[str, Any]) -> None:
    """Each support query names its approved answer document."""
    actual_labels = {query["id"]: query["expected_document_id"] for query in gold_set["queries"]}

    assert actual_labels == EXPECTED_GOLD_LABELS


def test_gold_queries_use_natural_language(
    documents: dict[str, Any], gold_set: dict[str, Any]
) -> None:
    """Each support query is a question and is not copied verbatim from the corpus."""
    corpus_text = " ".join(
        page for document in documents["documents"] for page in document["pages"]
    ).casefold()

    for query in gold_set["queries"]:
        text = query["query"]
        assert text.endswith("?")
        assert len(text.split()) >= 7
        assert text.casefold() not in corpus_text


def test_generator_creates_one_readable_pdf_per_document(
    generator: ModuleType, documents: dict[str, Any], tmp_path: Path
) -> None:
    """The public generator output contains every source page in the visibility folder."""
    output_dir = tmp_path / "corpus"
    paths = generator.generate_corpus(DOCUMENTS_PATH, output_dir)

    assert len(paths) == 20
    for document in documents["documents"]:
        path = output_dir / document["visibility"] / document["file_name"]
        assert path in paths
        reader = PdfReader(path)
        assert len(reader.pages) == len(document["pages"])
        expected_context = " ".join(document["context"].split())
        for page, source_page in zip(reader.pages, document["pages"], strict=True):
            extracted_text = " ".join(page.extract_text().split())
            assert expected_context in extracted_text
            assert " ".join(source_page.split()) in extracted_text


def test_generator_produces_byte_identical_output(generator: ModuleType, tmp_path: Path) -> None:
    """Two runs from the fixed source produce the same file names and bytes."""
    first = generator.generate_corpus(DOCUMENTS_PATH, tmp_path / "first")
    second = generator.generate_corpus(DOCUMENTS_PATH, tmp_path / "second")

    first_hashes = {
        path.relative_to(tmp_path / "first"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in first
    }
    second_hashes = {
        path.relative_to(tmp_path / "second"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in second
    }
    assert first_hashes == second_hashes


def test_generator_command_writes_to_requested_directory(tmp_path: Path) -> None:
    """The command accepts an output override and reports its generated destination."""
    output_dir = tmp_path / "command-output"
    result = subprocess.run(  # noqa: S603 - The command and script path are fixed.
        [sys.executable, str(GENERATOR_PATH), "--output", str(output_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"Generated 20 PDFs in {output_dir}"
    assert len(list(output_dir.rglob("*.pdf"))) == 20


def test_default_output_directory_is_gitignored(generator: ModuleType) -> None:
    """The on-demand binary corpus stays outside version control."""
    ignore_rules = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert generator.DEFAULT_OUTPUT == REPO_ROOT / "artifacts" / "meridian-corpus"
    assert "/artifacts/meridian-corpus/" in ignore_rules
