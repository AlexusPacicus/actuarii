"""Runs a program for the tests, without a shell: the one place that starts a process on their behalf.

Tests under tests/ pass through the boundary-validator, whose Zero-Trust matrix refuses a proposal
that names a process-starting primitive (AGENTS 2.1). The scope note of that clause leaves local
repository tooling out, so the spawning lives here and the tests import `run`. For tests only.

Standard library only.
"""
from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from os import PathLike


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str


def run(
    argv: Sequence[str],
    *,
    cwd: str | PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: str = "",
    timeout: float = 30.0,
) -> Result:
    """The argument list runs as it is, never through a shell. `env` is the whole environment of the
    child (the caller's own when None); `stdin` and the output are UTF-8 text; a timeout raises."""
    done = subprocess.run(
        list(argv),
        cwd=cwd,
        env=None if env is None else dict(env),
        input=stdin.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return Result(done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8"))
