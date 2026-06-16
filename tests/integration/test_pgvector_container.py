"""Integration test: Postgres + pgvector via testcontainers (worked example).

Demonstrates the harness pattern: the DB is started once per session with schema +
seed applied at instantiation, and `clean_db` resets the data between tests so a test
that writes does not leak into the next test's seed state.
"""

from typing import Protocol

import pytest

pytestmark = pytest.mark.integration


class Db(Protocol):
    """Subset of the conftest Database helper used by these tests (structural type)."""

    def has_extension(self, name: str = "vector") -> bool: ...

    def count_documents(self) -> int: ...

    def insert_document(self, text: str) -> None: ...


def test_pgvector_extension_available(clean_db: Db) -> None:
    assert clean_db.has_extension("vector")


def test_seed_data_present(clean_db: Db) -> None:
    assert clean_db.count_documents() == 2


def test_writes_are_isolated_between_tests(clean_db: Db) -> None:
    """Writing one row here must not affect the next test's seed state."""
    clean_db.insert_document("transient")
    assert clean_db.count_documents() == 3
    # clean_db resets before the next test, so test_seed_data_present still sees 2.
