"""Shared pytest fixtures.

Unit tests (the default run, `uv run pytest`) stay offline — no network, no DB, no
containers. Use fakes/stubs (FakeEmbedder, in-memory vector store, a stubbed
ChatAnthropic).

Integration tests (marked `integration`; run with `uv run pytest -m integration`) use
testcontainers to spin up an ephemeral Postgres + pgvector database. The container is
started once per session, the schema is applied and seed data inserted at
instantiation, and the `clean_db` fixture resets the data between tests so they are
isolated. Integration tests require Docker and the app extra (`uv sync --extra app`).

See docs/architecture.md -> Testing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

# Schema + seed used by the integration example. Replace with your real schema
# (migrations) and repositories once the application is built.
_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (
    id         SERIAL PRIMARY KEY,
    text       TEXT NOT NULL,
    embedding  vector(1024)  -- dim must match Embedder.dim(); nullable for seeding
);
"""

_SEED_SQL = """
INSERT INTO documents (text, embedding) VALUES
    ('harness scaffold note',          NULL),
    ('controller service repository',  NULL);
"""

_RESET_SQL = "TRUNCATE TABLE documents RESTART IDENTITY CASCADE;"


def _dsn_for_psycopg(url: str) -> str:
    """testcontainers returns a SQLAlchemy-style URL; strip the driver for psycopg."""
    return url.replace("postgresql+psycopg2", "postgresql").replace(
        "postgresql+psycopg", "postgresql"
    )


def _connect(dsn: str) -> Any:
    import psycopg  # lazy: keeps the default (offline) run import-free

    return psycopg.connect(_dsn_for_psycopg(dsn))


def _apply_schema_and_seed(dsn: str) -> None:
    with _connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(_SCHEMA_SQL)
        cur.execute(_SEED_SQL)
        conn.commit()


def _reset(dsn: str) -> None:
    """Truncate then re-seed so every test starts from the known seed state."""
    with _connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(_RESET_SQL)
        cur.execute(_SEED_SQL)
        conn.commit()


class Database:
    """Small helper bound to the session container's DSN.

    Encapsulates psycopg so tests don't import it directly and stay typed.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _conn(self) -> Any:
        return _connect(self._dsn)

    def has_extension(self, name: str = "vector") -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = %s", (name,))
            return cur.fetchone() is not None

    def count_documents(self) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM documents")
            return int(cur.fetchone()[0])

    def insert_document(self, text: str) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO documents (text, embedding) VALUES (%s, NULL)", (text,))
            conn.commit()


@pytest.fixture(scope="session")
def pg_dsn() -> Iterator[str]:
    """Start an ephemeral Postgres + pgvector container for the test session.

    Schema + seed data are applied once at container instantiation. Skipped if
    testcontainers isn't installed or the Docker daemon isn't reachable.
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError as exc:  # testcontainers not installed
        pytest.skip(f"testcontainers not installed: {exc}")

    try:
        import docker

        docker.from_env().ping()
    except Exception as exc:  # Docker daemon not reachable -> skip, don't fail
        pytest.skip(f"Docker not available: {exc}")

    with PostgresContainer(image="pgvector/pgvector:pg16") as pg:
        dsn = pg.get_connection_url()
        _apply_schema_and_seed(dsn)
        yield dsn


@pytest.fixture
def clean_db(pg_dsn: str) -> Database:
    """Per-test: reset seeded data so each test starts from the known seed state.

    Deletes data written by the previous test (truncate) and restores the seed, so
    tests are isolated and reproducible.
    """
    _reset(pg_dsn)
    return Database(pg_dsn)
