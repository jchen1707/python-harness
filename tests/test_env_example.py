"""Offline check that `.env.example` lists the four app keys with no secret values.

Pins the BAC-4 acceptance: `.env.example` lists the four keys and no secret values, so a
future edit that drops a key or fills in a real secret fails the suite. Plan: BAC-4
test-plan.md.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"

APP_KEYS = ["DATABASE_URL", "VOYAGE_API_KEY", "SIMILARITY_THRESHOLD", "LOG_LEVEL"]


def test_env_example_lists_four_app_keys() -> None:
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()

    for key in APP_KEYS:
        assert any(line.startswith(f"{key}=") for line in lines), key


def test_env_example_has_no_secret_value_for_voyage_key() -> None:
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("VOYAGE_API_KEY="):
            value = line.split("=", 1)[1]
            assert value.strip() == "", "VOYAGE_API_KEY must be empty, never a real key"
