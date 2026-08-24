"""Application startup behaviour at the composition root."""

import importlib
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


def test_startup_fails_when_the_voyage_key_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/support")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    sys.modules.pop("app.main", None)

    with pytest.raises(ValidationError) as error:
        importlib.import_module("app.main")

    assert {item["loc"] for item in error.value.errors()} == {("voyage_api_key",)}
