"""Guardrail tests for the `pytest -m integration` gate's `requires` probe.

The probe decides whether that gate runs at all: layer A reports the gate `unavailable`
and never executes it when this exits non-zero. A probe that answers "met" too readily
puts the failure it exists to prevent back on the agent's desk as a `fail`, so what these
assert is the *unmet* half — each missing half on its own, not just the happy path.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "scripts" / "integration_env_probe.py"


@pytest.fixture(scope="module")
def probe() -> ModuleType:
    """Load the probe by path — `scripts/` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_integration_env_probe_under_test", PROBE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_missing_modules_names_what_is_absent(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A module the interpreter cannot import is reported by name, not as a bare bool."""
    monkeypatch.setattr(probe, "REQUIRED_MODULES", ("sys", "a_module_that_does_not_exist"))
    assert probe.missing_modules() == ["a_module_that_does_not_exist"]


def test_docker_absent_from_path_is_not_up(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unfindable client is unmet. It must never fall through to 'probably fine'."""
    monkeypatch.setattr(probe.shutil, "which", lambda _name: None)
    assert probe.docker_is_up() is False


def test_docker_daemon_down_is_not_up(probe: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """The client exists and `docker info` exits non-zero: the daemon is not running."""
    monkeypatch.setattr(probe.shutil, "which", lambda _name: "/usr/local/bin/docker")
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda *_a, **_kw: subprocess.CompletedProcess(args=[], returncode=1),
    )
    assert probe.docker_is_up() is False


def test_either_half_missing_fails_the_probe(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Docker alone is not enough, and the app extra alone is not enough."""
    monkeypatch.setattr(probe, "docker_is_up", lambda: True)
    monkeypatch.setattr(probe, "missing_modules", lambda: ["psycopg"])
    assert probe.main() == 1

    monkeypatch.setattr(probe, "docker_is_up", lambda: False)
    monkeypatch.setattr(probe, "missing_modules", list)
    assert probe.main() == 1


def test_both_halves_present_passes(probe: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """With both there the gate is allowed to run — otherwise the probe blocks it for ever."""
    monkeypatch.setattr(probe, "docker_is_up", lambda: True)
    monkeypatch.setattr(probe, "missing_modules", list)
    assert probe.main() == 0


def test_failure_names_both_halves_and_the_fix(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The human reading a blocked run needs to be told what to install, not just that."""
    monkeypatch.setattr(probe, "docker_is_up", lambda: False)
    monkeypatch.setattr(probe, "missing_modules", lambda: ["psycopg"])
    assert probe.main() == 1
    err = capsys.readouterr().err
    assert "Docker" in err
    assert "psycopg" in err
    assert "uv sync --extra app" in err
