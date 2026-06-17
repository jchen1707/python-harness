"""Harness self-check (guardrail, not application logic).

Verifies the standard package layout is importable and the toolchain works before
any application code is written. Run with: uv run pytest
"""

import importlib


def test_app_package_importable() -> None:
    import app

    assert app.__name__ == "app"


def test_standard_layers_importable() -> None:
    """The standard layers exist as importable packages."""
    for subpkg in ("app.core", "app.api", "app.services", "app.repositories"):
        importlib.import_module(subpkg)
