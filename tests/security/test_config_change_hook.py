"""The ConfigChange hook (tools/hooks/block_config_changes.py): a change to the project settings, the local
settings or a skill is not applied to the running session, a change to the user or policy settings is, and a
payload the hook does not understand blocks the change. The real .claude/settings.json pins disableAllHooks to
false and registers the hook."""
import ast
import json
import shlex
import sys
from pathlib import Path

import pytest

from tools.audit.run_process import run

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "tools" / "hooks" / "block_config_changes.py"
SETTINGS = ROOT / ".claude" / "settings.json"
BLOCKED = ["project_settings", "local_settings", "skills"]
ALLOWED = ["user_settings", "policy_settings"]


def ask(stdin: str, tmp_path: Path):
    return run([sys.executable, str(HOOK)], cwd=tmp_path, stdin=stdin)


def change(source, file_path="/work/.claude/settings.local.json") -> str:
    return json.dumps({"hook_event_name": "ConfigChange", "source": source, "file_path": file_path})


# T1: which sources are blocked

@pytest.mark.parametrize("source", BLOCKED)
def test_a_change_of_the_project_the_local_or_the_skill_source_is_not_applied_and_names_the_file(source, tmp_path):
    done = ask(change(source, "/work/.claude/some/file.json"), tmp_path)
    assert done.returncode == 2
    assert "/work/.claude/some/file.json" in done.stderr
    assert "not applied to this session" in done.stderr
    assert "next session" in done.stderr
    assert done.stdout == ""


@pytest.mark.parametrize("source", ALLOWED)
def test_a_change_of_the_user_or_the_policy_settings_is_applied(source, tmp_path):
    done = ask(change(source), tmp_path)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_a_blocked_change_without_a_file_path_is_still_blocked(tmp_path):
    done = ask(json.dumps({"hook_event_name": "ConfigChange", "source": "local_settings"}), tmp_path)
    assert done.returncode == 2
    assert "not applied to this session" in done.stderr


# T2: the hook fails closed

@pytest.mark.parametrize("stdin", [
    pytest.param("", id="empty"),
    pytest.param("{", id="not-json"),
    pytest.param("[]", id="array"),
    pytest.param('"local_settings"', id="string"),
    pytest.param("null", id="null"),
    pytest.param("{}", id="no-source"),
    pytest.param('{"file_path": "x"}', id="no-source-with-path"),
    pytest.param('{"source": "other_settings"}', id="unknown-source"),
    pytest.param('{"source": ""}', id="empty-source"),
    pytest.param('{"source": null}', id="null-source"),
    pytest.param('{"source": ["local_settings"]}', id="list-source"),
    pytest.param('{"source": "LOCAL_SETTINGS"}', id="source-in-other-case"),
])
def test_a_payload_the_hook_does_not_understand_blocks_the_change(stdin, tmp_path):
    done = ask(stdin, tmp_path)
    assert done.returncode == 2
    assert done.stderr.startswith("[block_config_changes]")
    assert done.stdout == ""


def test_the_messages_cite_no_agents_clause(tmp_path):
    for stdin in (change("local_settings"), "{"):
        done = ask(stdin, tmp_path)
        assert done.stderr.startswith("[block_config_changes]")
        assert "AGENTS" not in done.stderr


# the hook starts under any interpreter the harness finds

def test_the_hook_imports_only_the_standard_library():
    tree = ast.parse(HOOK.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add("." * node.level + (node.module or "").split(".")[0])
    assert roots <= set(sys.stdlib_module_names), roots


def test_the_hook_postpones_annotations_and_parses_as_python_3_9():
    tree = ast.parse(HOOK.read_text(encoding="utf-8"), feature_version=(3, 9))
    assert any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


# T3: the real settings of this repository

def _settings() -> dict:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def test_the_project_settings_pin_disable_all_hooks_to_false():
    assert _settings()["disableAllHooks"] is False


def test_the_project_settings_register_the_hook_on_config_change_by_project_dir():
    [group] = _settings()["hooks"]["ConfigChange"]
    assert "matcher" not in group
    [hook] = group["hooks"]
    assert hook["type"] == "command"
    assert shlex.split(hook["command"]) == ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/block_config_changes.py"]
