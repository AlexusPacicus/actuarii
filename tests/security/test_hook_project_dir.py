"""Hook commands of .claude/settings.json run from any directory, as the harness runs them after a cd."""
import json
import os
import shlex
from pathlib import Path

import pytest

from tools.audit.run_process import run

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / ".claude" / "settings.json"
PREFIX = "$CLAUDE_PROJECT_DIR/tools/hooks/"

BOUNDARY = "require_boundary_validation.py"
CONTRACT = "require_contract_context.py"
CONFINE = "confine_review_reads.py"
BASH = "deny_python_escapes.py"
SESSION = "session_python_gate.sh"


def _commands() -> dict[str, str]:
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    commands = [
        hook["command"]
        for groups in hooks.values()
        for group in groups
        for hook in group["hooks"]
    ]
    return {shlex.split(command)[1].rsplit("/", 1)[-1]: command for command in commands}


def _run(script: str, tmp_path: Path, payload: dict | None = None, **extra: str):
    env = {"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": os.environ["PATH"], **extra}
    stdin = json.dumps(payload) if payload is not None else ""
    return run(["sh", "-c", _commands()[script]], cwd=tmp_path, env=env, stdin=stdin)


def _edit(path: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / path)}}


def test_the_five_hooks_are_registered():
    assert set(_commands()) == {BOUNDARY, CONTRACT, CONFINE, BASH, SESSION}


@pytest.mark.parametrize("script", [BOUNDARY, CONTRACT, CONFINE, BASH, SESSION])
def test_command_names_its_script_by_project_dir(script):
    argv = shlex.split(_commands()[script])
    assert len(argv) == 2 and argv[1] == PREFIX + script


@pytest.mark.parametrize("script", [BOUNDARY, CONTRACT])
def test_edit_of_an_ungoverned_path_is_allowed_from_another_directory(script, tmp_path):
    done = _run(script, tmp_path, _edit("not_governed_probe.md"))
    assert (done.returncode, done.stderr) == (0, "")


def test_edit_of_a_governed_path_without_receipt_is_denied_by_the_hook_itself(tmp_path):
    done = _run(BOUNDARY, tmp_path, _edit("tests/not_a_real_file_probe.py"))
    assert done.returncode == 2
    assert done.stderr.startswith("[require_boundary_validation]")
    assert "can't open file" not in done.stderr


def test_read_is_allowed_from_another_directory(tmp_path):
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "AGENTS.md")}}
    done = _run(CONFINE, tmp_path, payload)
    assert (done.returncode, done.stderr) == (0, "")


def test_bash_is_allowed_from_another_directory(tmp_path):
    payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    done = _run(BASH, tmp_path, payload)
    assert (done.returncode, done.stderr) == (0, "")


def test_session_hook_puts_tools_bin_first_on_the_path_from_another_directory(tmp_path):
    env_file = tmp_path / "env"
    done = _run(SESSION, tmp_path, CLAUDE_ENV_FILE=str(env_file))
    assert (done.returncode, done.stderr) == (0, "")
    assert env_file.read_text(encoding="utf-8") == f"export PATH='{ROOT / 'tools' / 'bin'}':\"$PATH\"\n"
