"""Guardrail tests for the MCP credential helper (`.agents/mcp_headers.py`).

Claude Code runs this script to authenticate the Linear MCP server. Two failure modes
matter, and both are silent without a test.

A slot name reaches a shell, so an unvalidated one is a command injection through
committed config. And an empty credential emits `Bearer ` and fails at the API with an
opaque 401, which reads as "the key is wrong" rather than "the store is empty" — the
exact confusion that cost time on this machine before.

These stay offline: the credential store is stubbed, so nothing here reads a real key.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HELPER_PATH = Path(__file__).resolve().parents[1] / ".claude" / "mcp_headers.py"

STORED_VALUE = "lin_api_notarealkey_0123456789"


@pytest.fixture(scope="module")
def helper() -> ModuleType:
    """Load the helper by path — `.claude` is not an importable package."""
    spec = importlib.util.spec_from_file_location("_mcp_headers_under_test", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_lookup(stdout: str, returncode: int = 0) -> tuple[Any, list[list[str]]]:
    """Replace subprocess.run with one returning a canned credential lookup.

    Returns the replacement and the list it records commands into, so a test asserts on
    what the helper tried to run.
    """
    captured: list[list[str]] = []

    def _run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")

    return _run, captured


@pytest.mark.parametrize(
    "slot",
    ["linear-py", "a", "linear-fro", "slot0", "0slot", "a" * 64],
)
def test_slot_pattern_accepts_a_credential_name(helper: ModuleType, slot: str) -> None:
    assert helper.SLOT_PATTERN.match(slot) is not None


@pytest.mark.parametrize(
    "slot",
    [
        "",
        "Linear",  # uppercase
        "linear py",  # space
        "-linear",  # leading dash
        "linear_py",  # underscore
        "a" * 65,  # too long
        "linear;whoami",  # command separator
        "linear$(whoami)",  # substitution
        "linear`whoami`",  # backtick substitution
        "../../etc/passwd",  # traversal
        "linear'; rm -rf /",  # quote break-out
        "linear\nwhoami",  # newline injection
    ],
)
def test_slot_pattern_rejects_an_injection_shaped_name(helper: ModuleType, slot: str) -> None:
    """The slot reaches a PowerShell literal, so validation is the boundary."""
    assert helper.SLOT_PATTERN.match(slot) is None


def test_credential_path_sits_under_the_claude_directory(helper: ModuleType) -> None:
    path = helper.credential_path("linear-py", Path("/home/someone"))
    assert path == Path("/home/someone/.claude/mcp-credentials/linear-py.cred")


def test_windows_lookup_reads_the_dpapi_credential(helper: ModuleType) -> None:
    command = helper.lookup_command("win32", "linear-py", Path("/home/someone"))
    assert command[0] == "powershell"
    assert "-NonInteractive" in command
    script = command[-1]
    assert "ConvertTo-SecureString" in script
    assert "linear-py.cred" in script


def test_windows_lookup_escapes_a_quote_in_the_home_path(helper: ModuleType) -> None:
    """A `'` in the path would close the PowerShell literal; doubling it escapes it."""
    script = helper.lookup_command("win32", "linear-py", Path("/home/o'brien"))[-1]
    assert "o''brien" in script


def test_macos_lookup_reads_the_keychain(helper: ModuleType) -> None:
    command = helper.lookup_command("darwin", "linear-py")
    assert command[0] == "security"
    assert "claude-mcp-linear-py" in command


def test_linux_lookup_reads_the_secret_service(helper: ModuleType) -> None:
    command = helper.lookup_command("linux", "linear-py")
    assert command[0] == "secret-tool"
    assert "claude-mcp-linear-py" in command


def test_headers_carry_the_token_as_a_bearer(helper: ModuleType) -> None:
    assert helper.headers(STORED_VALUE) == {"Authorization": f"Bearer {STORED_VALUE}"}


def test_main_writes_the_headers_as_json(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run, _ = stub_lookup(f"{STORED_VALUE}\n")
    monkeypatch.setattr(helper.subprocess, "run", run)

    assert helper.main(["mcp_headers.py", "linear-py"], platform="win32") == 0
    assert json.loads(capsys.readouterr().out) == {"Authorization": f"Bearer {STORED_VALUE}"}


def test_main_refuses_a_slot_without_reaching_the_shell(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An invalid slot must fail before any lookup command is built or run."""
    run, captured = stub_lookup(STORED_VALUE)
    monkeypatch.setattr(helper.subprocess, "run", run)

    assert helper.main(["mcp_headers.py", "linear;whoami"], platform="win32") == 1
    assert captured == []
    assert capsys.readouterr().out == ""


def test_main_reports_a_missing_credential(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run, _ = stub_lookup("", returncode=1)
    monkeypatch.setattr(helper.subprocess, "run", run)

    assert helper.main(["mcp_headers.py", "linear-py"], platform="win32") == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "linear-py" in captured.err


def test_main_rejects_an_empty_credential_rather_than_sending_a_bare_bearer(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed paste stores an empty value that otherwise looks like a working one."""
    run, _ = stub_lookup("   \n")
    monkeypatch.setattr(helper.subprocess, "run", run)

    assert helper.main(["mcp_headers.py", "linear-py"], platform="win32") == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "store it again" in captured.err


def test_main_reports_a_missing_credential_tool(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A machine without `secret-tool` must fail with a diagnostic, not a traceback."""

    def _run(_cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("secret-tool")

    monkeypatch.setattr(helper.subprocess, "run", _run)

    assert helper.main(["mcp_headers.py", "linear-py"], platform="linux") == 1
    assert "secret-tool" in capsys.readouterr().err


def test_a_diagnostic_never_carries_the_token(
    helper: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The helper runs with the credential in scope; stderr may reach a pasted log."""
    run, _ = stub_lookup(STORED_VALUE, returncode=1)
    monkeypatch.setattr(helper.subprocess, "run", run)

    helper.main(["mcp_headers.py", "linear-py"], platform="win32")
    assert STORED_VALUE not in capsys.readouterr().err


def test_mcp_config_uses_docker_mcp_toolkit() -> None:
    """Docker MCP Toolkit must own the Linear connection and its credential."""
    config = json.loads((Path(__file__).resolve().parents[1] / ".mcp.json").read_text())
    linear = config["mcpServers"]["linear"]

    assert "headers" not in linear
    assert "LINEAR_API_KEY" not in json.dumps(config)
    assert linear == {"command": "docker", "args": ["mcp", "gateway", "run"]}


def test_every_enabled_mcp_server_is_defined() -> None:
    """`enabledMcpjsonServers` named `pyright-lsp` for months; `.mcp.json` never defined it.

    Neither file is wrong on its own, so nothing failed. The server was simply absent from
    every Claude session, while `AGENTS.md` spent a section telling agents to prefer it to
    grep. Only the pair carries the defect, so only the pair can be asserted.
    """
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))

    assert sorted(settings["enabledMcpjsonServers"]) == sorted(config["mcpServers"])


def test_the_pyright_launcher_is_shared_by_both_harnesses() -> None:
    """The launcher lived under `.codex/`, so only Codex could reasonably reference it.

    On `v2` the canonical directory is `.agents/`; a launcher both harnesses start belongs
    there, and a harness-specific path is how one of them ends up without the server.
    """
    root = Path(__file__).resolve().parents[1]
    launcher = ".agents/start-pyright-mcp.sh"

    assert (root / launcher).is_file()
    config = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
    assert config["mcpServers"]["pyright-lsp"]["args"] == [launcher]
    assert launcher in (root / ".codex" / "config.toml").read_text(encoding="utf-8")
