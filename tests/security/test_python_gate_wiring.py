"""Wiring test: .claude/settings.json actually runs the two hooks of the Python gate (AGENTS
2.5) -- the SessionStart PATH shim and the PreToolUse Bash deny hook -- asserted as parsed
structure (the way test_config_perimeter.py asserts the permission matrix), never as text.
Neither hook script's own behaviour is exercised here; that is test_python_gate.py and
test_python_gate_bash_hook.py.

Normative: AGENTS.md 2.5, 6.2
"""
import copy
import json
import re
import shlex
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / ".claude" / "settings.json"

SESSION_COMMAND = ["sh", "tools/hooks/session_python_gate.sh"]
BASH_COMMAND = ["python3", "tools/hooks/deny_python_escapes.py"]


def _settings() -> dict:
    return json.loads(CLAUDE.read_text(encoding="utf-8"))


def _base_settings() -> dict:
    """Minimal settings dict wired exactly as B1/B2 require, for mutation tests."""
    return {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": " ".join(SESSION_COMMAND)}]}
            ],
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": " ".join(BASH_COMMAND)}]}
            ],
        }
    }


def _session_hook_wired(settings: dict, root: Path = ROOT) -> bool:
    """B1: a SessionStart group with no 'matcher' key runs SESSION_COMMAND, and the script it
    names exists under `root` (B3)."""
    for group in settings.get("hooks", {}).get("SessionStart", []):
        if "matcher" in group:
            continue
        for hook in group.get("hooks", []):
            if hook.get("type") != "command":
                continue
            command = hook.get("command")
            if isinstance(command, str) and shlex.split(command) == SESSION_COMMAND:
                return (root / SESSION_COMMAND[1]).is_file()
    return False


def _bash_hook_wired(settings: dict, root: Path = ROOT) -> bool:
    """B2: a PreToolUse group whose matcher fullmatches 'Bash' runs BASH_COMMAND, and the
    script it names exists under `root` (B3)."""
    for group in settings.get("hooks", {}).get("PreToolUse", []):
        matcher = group.get("matcher")
        if not isinstance(matcher, str):
            continue
        try:
            if not re.fullmatch(matcher, "Bash"):
                continue
        except re.error:
            continue
        for hook in group.get("hooks", []):
            if hook.get("type") != "command":
                continue
            command = hook.get("command")
            if isinstance(command, str) and shlex.split(command) == BASH_COMMAND:
                return (root / BASH_COMMAND[1]).is_file()
    return False


def _mutate(fn) -> dict:
    settings = copy.deepcopy(_base_settings())
    fn(settings)
    return settings


# T1/T2: the real file (guard -- green from the start; B3 covered by the same call, since
# root defaults to the real repository root)


def test_session_gate_is_wired_in_the_real_settings():
    assert _session_hook_wired(_settings())


def test_bash_gate_is_wired_in_the_real_settings():
    assert _bash_hook_wired(_settings())


# T3: mutations B1 must reject


SESSION_REJECTIONS = {
    "sessionstart_removed": lambda s: s["hooks"].__setitem__("SessionStart", []),
    "gate_hook_removed_from_group": lambda s: s["hooks"]["SessionStart"][0].__setitem__("hooks", []),
    "matcher_excludes_a_source": lambda s: s["hooks"]["SessionStart"][0].__setitem__("matcher", "startup"),
    "command_names_another_script": lambda s: s["hooks"]["SessionStart"][0]["hooks"][0].__setitem__(
        "command", "sh tools/hooks/other_gate.sh"),
    "command_run_by_another_interpreter": lambda s: s["hooks"]["SessionStart"][0]["hooks"][0].__setitem__(
        "command", "bash tools/hooks/session_python_gate.sh"),
}


@pytest.mark.parametrize("name", sorted(SESSION_REJECTIONS))
def test_session_mutation_is_rejected(name):
    assert not _session_hook_wired(_mutate(SESSION_REJECTIONS[name]))


# T4: mutations B2 must reject


BASH_REJECTIONS = {
    "bash_group_removed": lambda s: s["hooks"].__setitem__("PreToolUse", []),
    "matcher_does_not_fullmatch_edit_write": lambda s: s["hooks"]["PreToolUse"][0].__setitem__(
        "matcher", "Edit|Write"),
    "matcher_does_not_fullmatch_superstring": lambda s: s["hooks"]["PreToolUse"][0].__setitem__(
        "matcher", "Bashx"),
    "command_names_another_script": lambda s: s["hooks"]["PreToolUse"][0]["hooks"][0].__setitem__(
        "command", "python3 tools/hooks/other_hook.py"),
    "command_run_by_another_interpreter": lambda s: s["hooks"]["PreToolUse"][0]["hooks"][0].__setitem__(
        "command", "python3.12 tools/hooks/deny_python_escapes.py"),
    "hook_type_not_command": lambda s: s["hooks"]["PreToolUse"][0]["hooks"][0].__setitem__(
        "type", "other"),
}


@pytest.mark.parametrize("name", sorted(BASH_REJECTIONS))
def test_bash_mutation_is_rejected(name):
    assert not _bash_hook_wired(_mutate(BASH_REJECTIONS[name]))


# T5: accepted variants a text-level check would wrongly reject


def test_matcher_alternation_that_still_fullmatches_bash_is_accepted():
    settings = _mutate(lambda s: s["hooks"]["PreToolUse"][0].__setitem__("matcher", "Bash|Edit"))
    assert _bash_hook_wired(settings)


def test_extra_whitespace_inside_the_command_is_accepted():
    settings = _mutate(lambda s: s["hooks"]["PreToolUse"][0]["hooks"][0].__setitem__(
        "command", "python3   tools/hooks/deny_python_escapes.py"))
    assert _bash_hook_wired(settings)
    settings = _mutate(lambda s: s["hooks"]["SessionStart"][0]["hooks"][0].__setitem__(
        "command", "sh   tools/hooks/session_python_gate.sh"))
    assert _session_hook_wired(settings)


# T6: a correctly wired command naming a script that does not exist on disk (B3)


def test_wired_command_naming_a_missing_script_is_rejected(tmp_path):
    settings = _base_settings()
    assert not _session_hook_wired(settings, root=tmp_path)
    assert not _bash_hook_wired(settings, root=tmp_path)
