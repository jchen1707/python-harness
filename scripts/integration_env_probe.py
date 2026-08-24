"""Exit zero only when the `pytest -m integration` gate's environment is actually here.

Layer A runs this as that gate's `requires` probe: immediately before the gate, and only
when the gate was going to run anyway. Non-zero and the gate is reported `unavailable`
and never runs, which reaches an agent as "the environment is missing" rather than as a
`fail` it will try to repair by writing code.

The gate needs two separate things and the obvious one-command probe covers only one of
them:

* **Docker.** `testcontainers` starts an ephemeral Postgres + pgvector. `docker info`
  answers this -- the client binary existing is not enough, the daemon has to be up.
* **The app extra.** `psycopg` and `pgvector` live in the `app` extra, not in the default
  sync, and pytest collects the whole `tests/` tree before any marker filter applies --
  so a missing extra fails collection repo-wide with `ModuleNotFoundError`, not just the
  integration tests. Measured on a host with Docker running and the extra unsynced:
  `uv run pytest -m integration` errored on `import pydantic` in three files.

Stdlib only, and imports the extra's packages by spec lookup rather than by importing
them, so this stays fast and cannot fail for a reason of its own.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys

# The app-extra packages the integration path actually reaches: conftest connects with
# psycopg and the schema declares a pgvector column. testcontainers is in the dev group,
# so it is present whenever pytest is.
REQUIRED_MODULES = ("psycopg", "pgvector")


def missing_modules() -> list[str]:
    """Names from REQUIRED_MODULES that this interpreter cannot import."""
    return [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]


def docker_is_up() -> bool:
    """Whether a Docker daemon is reachable. False if the client is not installed either."""
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        # S603 is suppressed: the argv is a constant plus a PATH lookup, no shell,
        # no caller input.
        return subprocess.run([docker, "info"], capture_output=True).returncode == 0  # noqa: S603
    except OSError:
        return False


def main() -> int:
    problems: list[str] = []
    if not docker_is_up():
        problems.append("Docker is not running (`docker info` failed)")
    if missing := missing_modules():
        problems.append(f"the app extra is not installed (no {', '.join(missing)})")
    if not problems:
        return 0
    for problem in problems:
        print(problem, file=sys.stderr)
    print("run: uv sync --extra app, and start Docker", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
