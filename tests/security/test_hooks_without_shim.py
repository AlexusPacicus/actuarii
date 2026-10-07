"""Every hook command of .claude/settings.json decides the same with the shim first on the PATH, without it, and under the system Python.

The harness runs each command with whatever PATH it has. A hook that cannot start exits non-zero, which the harness may
read as a broken hook and not as a denial, so a difference between environments is a gate that opens.
"""
import functools
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.audit.run_process import run

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / ".claude" / "settings.json"
SHIM_DIR = ROOT / "tools" / "bin"
SYSTEM_PYTHON = Path("/usr/bin/python3")
SYSTEM_PATH = "/usr/bin:/bin"
QUOTE = chr(34)
PATH_LINE = "export PATH='" + str(SHIM_DIR) + "':" + QUOTE + "$PATH" + QUOTE + "\n"
INHERITED = {name: os.environ[name] for name in ("TMPDIR",) if name in os.environ}
# On macOS /usr/bin/python3 is an xcrun stub: where it cannot write its cache (inside the Bash sandbox) it says so
# on stderr and then runs the interpreter, so that line is not the hook's.
XCRUN_NOISE = "python3: error: couldn't create cache file"

SHIM_FIRST = "shim-first"
NO_SHIM = "no-shim"
SYSTEM = "system-python"

BOUNDARY = "require_boundary_validation.py"
CONTRACT = "require_contract_context.py"
CONFINE = "confine_review_reads.py"
BASH = "deny_python_escapes.py"
SESSION = "session_python_gate.sh"
ANNOUNCE = "announce_governance.py"
CONFIG = "block_config_changes.py"


@dataclass(frozen=True)
class Case:
    id: str
    script: str
    payload: dict | None
    code: int
    stderr_prefix: str = ""
    stdout_prefix: str = ""
    env_file: str = ""


def _edit(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / path), "old_string": "a", "new_string": "b"}}


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _config(source: str) -> dict:
    return {"hook_event_name": "ConfigChange", "source": source, "file_path": "/work/.claude/settings.json"}


CASES = [
    Case("boundary-denies-a-governed-edit-without-receipt", BOUNDARY, _edit("tests/not_a_real_file_probe.py"), 2,
         stderr_prefix="[require_boundary_validation] "),
    Case("boundary-allows-an-ungoverned-edit", BOUNDARY, _edit("not_governed_probe.md"), 0),
    Case("contract-allows-an-edit-without-registry", CONTRACT, _edit("not_governed_probe.md"), 0),
    Case("confine-allows-a-read-without-lock", CONFINE,
         {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "AGENTS.md")}}, 0),
    Case("bash-denies-an-interpreter-named-by-path", BASH, _bash("/usr/bin/python3 -c x"), 2,
         stderr_prefix="[deny_python_escapes] R1"),
    Case("bash-allows-git-status", BASH, _bash("git status"), 0),
    Case("config-blocks-a-project-settings-change", CONFIG, _config("project_settings"), 2,
         stderr_prefix="[block_config_changes] /work/.claude/settings.json (project_settings)"),
    Case("config-applies-a-user-settings-change", CONFIG, _config("user_settings"), 0),
    Case("announce-names-the-source-of-the-rules", ANNOUNCE, None, 0,
         stdout_prefix="actuarii: the governance rules come from "),
    Case("session-writes-the-path-line", SESSION, None, 0, env_file=PATH_LINE),
]


def _commands() -> dict[str, str]:
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    commands = [
        hook["command"]
        for groups in hooks.values()
        for group in groups
        for hook in group["hooks"]
    ]
    return {shlex.split(command)[1].rsplit("/", 1)[-1]: command for command in commands}


@functools.cache
def _system_python() -> tuple[str, str]:
    """The version the system interpreter reports, and why it cannot run when it does not (one is empty)."""
    if not SYSTEM_PYTHON.exists():
        return "", f"{SYSTEM_PYTHON} does not exist"
    done = run([str(SYSTEM_PYTHON), "--version"], env={"PATH": SYSTEM_PATH, **INHERITED}, timeout=10.0)
    if done.returncode != 0:
        return "", f"{SYSTEM_PYTHON} --version exited {done.returncode}: {done.stderr.strip()}"
    return done.stdout.strip(), ""


def _path(environment: str, tmp_path: Path) -> str:
    if environment == SYSTEM:
        return SYSTEM_PATH
    link_dir = tmp_path / "pybin"
    link_dir.mkdir(exist_ok=True)
    link = link_dir / "python3"
    if not link.is_symlink():
        link.symlink_to(sys.executable)
    entries = [str(link_dir), SYSTEM_PATH]
    if environment == SHIM_FIRST:
        entries.insert(0, str(SHIM_DIR))
    return os.pathsep.join(entries)


def _require(environment: str, record_property) -> None:
    if environment != SYSTEM:
        return
    version, reason = _system_python()
    if reason:
        pytest.skip(reason)
    record_property("system_python", version)


def _available() -> list[str]:
    return [SHIM_FIRST, NO_SHIM] + ([] if _system_python()[1] else [SYSTEM])


def _decide(case: Case, environment: str, tmp_path: Path) -> tuple:
    env_file = tmp_path / f"claude_env_{environment}"
    env = {"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": _path(environment, tmp_path), **INHERITED}
    if case.env_file:
        env["CLAUDE_ENV_FILE"] = str(env_file)
    stdin = json.dumps(case.payload) if case.payload is not None else ""
    done = run(["sh", "-c", _commands()[case.script]], cwd=tmp_path, env=env, stdin=stdin)
    written = env_file.read_text(encoding="utf-8") if case.env_file else ""
    stderr = "".join(line for line in done.stderr.splitlines(keepends=True) if not line.startswith(XCRUN_NOISE))
    return done.returncode, stderr, done.stdout.split("\n", 1)[0], written


def test_the_cases_cover_every_registered_hook():
    assert {case.script for case in CASES} == set(_commands())


@pytest.mark.parametrize("environment, expected", [
    (SHIM_FIRST, str(SHIM_DIR / "python3")),
    (NO_SHIM, None),
    (SYSTEM, str(SYSTEM_PYTHON)),
])
def test_the_environment_resolves_python3_as_declared(environment, expected, tmp_path, record_property):
    _require(environment, record_property)
    env = {"PATH": _path(environment, tmp_path)}
    done = run(["sh", "-c", "command -v python3"], cwd=tmp_path, env=env)
    assert done.returncode == 0
    assert done.stdout.strip() == (expected or str(tmp_path / "pybin" / "python3"))


@pytest.mark.parametrize("environment", [SHIM_FIRST, NO_SHIM, SYSTEM])
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_a_hook_gives_its_known_decision(case, environment, tmp_path, record_property):
    _require(environment, record_property)
    code, stderr, stdout, written = _decide(case, environment, tmp_path)
    assert (code, written) == (case.code, case.env_file), stderr
    assert (stderr == "") if code == 0 else stderr.startswith(case.stderr_prefix), stderr
    assert stdout.startswith(case.stdout_prefix), stdout


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_a_hook_gives_the_same_decision_in_every_environment(case, tmp_path):
    decisions = {environment: _decide(case, environment, tmp_path) for environment in _available()}
    assert len(set(decisions.values())) == 1, decisions
