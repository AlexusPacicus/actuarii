"""SessionStart hook: the kit says what it governs in this session and where the rule comes from, and never blocks.

The text is built from tools/project_config, so it cannot diverge from what the gates apply. In-process tests
capture stdout; only the import-failure tests spawn the hook, with an isolated interpreter.
"""
import json
import os
import sys
from pathlib import Path

import pytest

from tools import project_config
from tools.audit import run_process
from tools.hooks import announce_governance

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "tools" / "hooks" / "announce_governance.py"
GATE_TOOL = "mcp__boundary-validator__validate_proposal"
VALID = {
    "schema": "actuarii-config/1",
    "governed_paths": ["docs/**", "src/*.py", "NOTES.md"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 120,
}
REVIEW = {"procedure": "skills/review.md", "base_docs": [], "records": "audit/records", "denied": []}


def announce(capsys) -> str:
    assert announce_governance.main() == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert lines and lines[0].startswith("actuarii:")
    assert all(line.startswith(("actuarii:", " ")) for line in lines)
    return captured.out


def receipt_paths(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("    ")]


def python_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("  Python"))


# T1: a valid configuration is announced whole


def test_a_valid_configuration_names_its_source_window_and_every_governed_path(config_file, capsys):
    config_file(VALID)
    text = announce(capsys)
    assert project_config.CONFIG_NAME in text.splitlines()[0]
    assert GATE_TOOL in text
    assert "120 s" in text
    assert receipt_paths(text) == [project_config.CONFIG_NAME, "docs/**", "src/*.py", "NOTES.md"]


def test_the_governed_paths_keep_their_configured_order(config_file, capsys):
    config_file({**VALID, "governed_paths": ["z.md", "a/**", "m.md"]})
    assert receipt_paths(announce(capsys)) == [project_config.CONFIG_NAME, "z.md", "a/**", "m.md"]


def test_a_configured_registry_is_named_and_listed_among_the_receipts(config_file, capsys):
    config_file({**VALID, "contract_registry": "kit/registry.json"})
    text = announce(capsys)
    assert "  Contract registry: kit/registry.json" in text.splitlines()
    assert receipt_paths(text)[:2] == [project_config.CONFIG_NAME, "kit/registry.json"]


def test_without_a_registry_the_announcement_says_none(config_file, capsys):
    config_file(VALID)
    assert "  Contract registry: none" in announce(capsys).splitlines()


def test_a_configured_blind_review_names_its_procedure_and_records(config_file, capsys):
    config_file({**VALID, "review": REVIEW})
    assert "  Blind review: procedure skills/review.md, records in audit/records" in announce(capsys).splitlines()


@pytest.mark.parametrize("configured", [True, False])
def test_without_a_blind_review_the_announcement_says_none(config_file, capsys, configured):
    if configured:
        config_file(VALID)
    assert "  Blind review: none" in announce(capsys).splitlines()


@pytest.mark.parametrize("dirs, expected", [
    ([], "python_script_dirs: none"),
    (["scripts", "exp/x"], "python_script_dirs: scripts, exp/x"),
    (["."], "python_script_dirs: . (the whole repository)"),
])
def test_python_runs_from_the_kit_directory_and_the_configured_directories(config_file, capsys, dirs, expected):
    config_file({**VALID, "python_script_dirs": dirs})
    line = python_line(announce(capsys))
    assert "committed scripts" in line
    assert "tools/" in line
    assert line.endswith(expected)


def test_the_declared_limit_says_bash_writes_pass_no_gate(config_file, capsys):
    config_file(VALID)
    assert any("Bash" in line and "limit" in line for line in announce(capsys).splitlines())


# T2: the built-in minimum and an invalid configuration are never announced as a valid file


def test_without_a_file_the_built_in_minimum_is_announced_as_such(config_file, capsys):
    text = announce(capsys)
    assert project_config.BUILT_IN_SOURCE in text.splitlines()[0]
    assert "900 s" in text
    assert receipt_paths(text) == list(dict.fromkeys((project_config.CONFIG_NAME, *project_config.BUILT_IN_PATHS)))
    assert receipt_paths(text) == [".actuarii.json", "AGENTS.md", "CLAUDE.md", ".claude/**", ".mcp.json", "tools/**"]
    assert "  Contract registry: none" in text.splitlines()
    assert python_line(text).endswith("python_script_dirs: . (the whole repository)")


@pytest.mark.parametrize("content", ["{", '{"schema": "other"}', "[]"])
def test_an_invalid_configuration_says_the_error_and_the_general_denial(config_file, capsys, content):
    config_file(content)
    with pytest.raises(project_config.ConfigError) as error:
        project_config.load()
    text = announce(capsys)
    first = text.splitlines()[0]
    assert "invalid" in first and project_config.CONFIG_NAME in first
    assert str(error.value) in text
    assert "every Edit/Write inside the repository is denied" in text
    assert f"except {project_config.CONFIG_NAME}" in text
    assert f"{project_config.DEFAULT_WINDOW} s" in text
    assert "only from tools/" in python_line(text)
    assert "repair" in text.splitlines()[-1]
    assert receipt_paths(text) == []


# T3: what is announced is what the gates apply


@pytest.mark.parametrize("config", [
    VALID,
    {**VALID, "contract_registry": "kit/registry.json"},
    {**VALID, "governed_paths": ["a/**/b.md", "*.toml"], "receipt_window_seconds": 3600},
    None,
])
def test_every_announced_path_is_governed_by_the_project_configuration(config_file, capsys, config):
    if config is not None:
        config_file(config)
    for path in receipt_paths(announce(capsys)):
        governed = project_config.governance(path)
        assert governed is not None, path
        assert governed.window_seconds == project_config.load().receipt_window_seconds


def test_the_announced_window_is_the_one_the_gate_applies(config_file, capsys):
    config_file({**VALID, "receipt_window_seconds": 777})
    assert "777 s" in announce(capsys)
    assert project_config.governance("NOTES.md").window_seconds == 777


def test_the_text_has_no_escape_sequences_and_no_foreign_names(config_file, capsys):
    config_file(VALID)
    text = announce(capsys)
    assert "\x1b" not in text
    assert not {"Traianus", "AGENTS", "clause"} & set(text.split())


# T4: never blocks, never writes to stderr, not even with a broken project configuration


def spawn_hook(tmp_path, config_source):
    """The hook, copied into a throwaway repository whose project configuration module is `config_source`
    (None: absent), run with an isolated interpreter."""
    root = tmp_path / "kit"
    (root / "tools" / "hooks").mkdir(parents=True)
    (root / "tools" / "__init__.py").write_text("", encoding="utf-8")
    copy = root / "tools" / "hooks" / HOOK.name
    copy.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    if config_source is not None:
        (root / "tools" / "project_config.py").write_text(config_source, encoding="utf-8")
    return run_process.run([sys.executable, "-I", str(copy)], stdin="")


def test_a_working_project_configuration_lets_the_spawned_hook_announce(tmp_path):
    done = spawn_hook(tmp_path, (REPO_ROOT / "tools" / "project_config.py").read_text(encoding="utf-8"))
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout.startswith("actuarii:")


@pytest.mark.parametrize("source, cause", [
    pytest.param(None, "project_config", id="absent"),
    pytest.param("raise RuntimeError('boom')\n", "boom", id="raises"),
    pytest.param("def broken(:\n", "SyntaxError", id="syntax-error"),
    pytest.param("CONFIG_NAME = 1\n", "cannot import name", id="incomplete"),
])
def test_a_project_configuration_that_cannot_be_imported_is_announced_with_exit_0(tmp_path, source, cause):
    done = spawn_hook(tmp_path, source)
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout.startswith("actuarii:")
    assert "could not be imported" in done.stdout
    assert "denies every Edit/Write" in done.stdout
    assert cause in done.stdout


# T7: the Bash sandbox and the commit-integrity hook are announced, and neither can make the announcement fail

HOOK_SOURCE = "tools/git/pre-commit"
HOOK_TEXT = b"#!/bin/sh\nexit 0\n"
DIRECTORY = object()


@pytest.fixture
def kit_root(tmp_path, monkeypatch):
    """A repository standing in for the real one: the announcement reads its settings and its hooks directory."""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "root"
    (root / "tools" / "git").mkdir(parents=True)
    (root / HOOK_SOURCE).write_bytes(HOOK_TEXT)
    assert run_process.run(["git", "init", "-q"], cwd=root).returncode == 0
    monkeypatch.setattr(announce_governance, "REPO_ROOT", root)
    return root


def write_settings(root, content):
    path = root / ".claude" / "settings.json"
    if content is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is DIRECTORY:
        path.mkdir()
    elif isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def install_hook(root, content=HOOK_TEXT, mode=0o755, where=".git/hooks"):
    path = root / where / "pre-commit"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(mode)


def line_starting(text, start):
    return next(line for line in text.splitlines() if line.startswith(start))


def test_an_enabled_sandbox_is_announced_as_on(config_file, kit_root, capsys):
    config_file(VALID)
    write_settings(kit_root, {"sandbox": {"enabled": True}})
    assert line_starting(announce(capsys), "  Bash sandbox:").startswith("  Bash sandbox: on")


@pytest.mark.parametrize("content", [
    pytest.param(None, id="no-file"),
    pytest.param(DIRECTORY, id="unreadable"),
    pytest.param(b"\xff\xfe", id="not-utf-8"),
    pytest.param("{", id="not-json"),
    pytest.param([], id="array"),
    pytest.param({}, id="no-sandbox-key"),
    pytest.param({"sandbox": {}}, id="no-enabled-key"),
    pytest.param({"sandbox": {"enabled": False}}, id="disabled"),
    pytest.param({"sandbox": {"enabled": "true"}}, id="enabled-as-text"),
    pytest.param({"sandbox": {"enabled": 1}}, id="enabled-as-number"),
    pytest.param({"sandbox": True}, id="sandbox-not-an-object"),
])
def test_anything_but_an_enabled_sandbox_is_announced_as_off(config_file, kit_root, capsys, content):
    config_file(VALID)
    write_settings(kit_root, content)
    assert line_starting(announce(capsys), "  Bash sandbox:").startswith("  Bash sandbox: off")


def test_the_declared_limit_holds_with_and_without_the_sandbox(config_file, capsys):
    config_file(VALID)
    line = line_starting(announce(capsys), "  Declared limit:")
    assert "with the Bash sandbox on, Bash cannot write the governed paths" in line
    assert "with it off, writes made through Bash do not pass these gates" in line


def test_an_installed_hook_is_announced_as_installed(config_file, kit_root, capsys):
    config_file(VALID)
    install_hook(kit_root)
    assert line_starting(announce(capsys), "  Commit integrity hook:").startswith(
        "  Commit integrity hook: installed"
    )


def test_the_hook_git_would_run_is_the_one_checked_when_core_hooks_path_is_set(config_file, kit_root, capsys):
    config_file(VALID)
    assert run_process.run(["git", "config", "core.hooksPath", "custom"], cwd=kit_root).returncode == 0
    install_hook(kit_root, where="custom")
    assert "  Commit integrity hook: installed" in announce(capsys)


@pytest.mark.parametrize("installed", [
    pytest.param(None, id="absent"),
    pytest.param({"content": b"#!/bin/sh\nexit 1\n"}, id="other-content"),
    pytest.param({"mode": 0o644}, id="not-executable"),
])
def test_a_hook_that_is_missing_changed_or_not_executable_is_not_installed_and_the_way_is_given(
    config_file, kit_root, capsys, installed
):
    config_file(VALID)
    if installed is not None:
        install_hook(kit_root, **installed)
    line = line_starting(announce(capsys), "  Commit integrity hook:")
    assert line.startswith("  Commit integrity hook: not installed")
    assert f"copy {HOOK_SOURCE} to .git/hooks/pre-commit and make it executable" in line


def test_a_directory_that_is_not_a_repository_is_announced_as_cannot_tell(config_file, kit_root, tmp_path, monkeypatch, capsys):
    config_file(VALID)
    plain = tmp_path / "plain"
    (plain / "tools" / "git").mkdir(parents=True)
    (plain / HOOK_SOURCE).write_bytes(HOOK_TEXT)
    monkeypatch.setattr(announce_governance, "REPO_ROOT", plain)
    assert line_starting(announce(capsys), "  Commit integrity hook:").startswith(
        "  Commit integrity hook: cannot tell"
    )


def test_a_missing_hook_source_is_announced_as_cannot_tell(config_file, kit_root, capsys):
    config_file(VALID)
    (kit_root / HOOK_SOURCE).unlink()
    assert line_starting(announce(capsys), "  Commit integrity hook:").startswith(
        "  Commit integrity hook: cannot tell"
    )


def test_a_git_that_cannot_start_is_announced_as_cannot_tell(config_file, kit_root, tmp_path, monkeypatch, capsys):
    config_file(VALID)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert line_starting(announce(capsys), "  Commit integrity hook:").startswith(
        "  Commit integrity hook: cannot tell"
    )


def test_an_error_while_asking_git_is_announced_as_cannot_tell_and_the_announcement_still_succeeds(
    config_file, kit_root, monkeypatch, capsys
):
    config_file(VALID)

    def broken(argv, **kwargs):
        raise RuntimeError("git went away")

    monkeypatch.setattr(run_process, "run", broken)
    line = line_starting(announce(capsys), "  Commit integrity hook:")
    assert line.startswith("  Commit integrity hook: cannot tell") and "git went away" in line
