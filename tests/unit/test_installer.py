"""The installer (tools/install.py): one command puts the kit into an existing git repository without overwriting anything.

Every case runs the installer as the person would, a process started from the clone on a repository under tmp_path, with
HOME pointed at a temporary directory so the user's own settings are never read or written. What a case checks is the
state of the target afterwards: what was copied, what was merged, what was left alone, and that a conflict or a dry run
writes nothing.
"""
import copy
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from tests.security.test_sandbox_settings import STRICT, expected_deny_write, sandbox_problems
from tools.audit.run_process import run

CLONE = Path(__file__).resolve().parents[2]
INSTALLER = CLONE / "tools" / "install.py"
SYSTEM_PYTHON = Path("/usr/bin/python3")
SYSTEM_PATH = "/usr/bin:/bin"
PREFIX = "actuarii install: "
DRY_RUN_CLOSING = "dry run: nothing was written"
KIT_TREES = ("tools", ".claude/agents", ".claude/skills")
SERVER = "boundary-validator"
CLONE_SETTINGS = json.loads((CLONE / ".claude" / "settings.json").read_text(encoding="utf-8"))
CLONE_SERVER = json.loads((CLONE / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][SERVER]
PRE_COMMIT_SOURCE = CLONE / "tools" / "git" / "pre-commit"
EXAMPLE_CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["AGENTS.md", "CLAUDE.md", ".claude/**", ".mcp.json", "tools/**"],
    "python_script_dirs": ["."],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 900,
}


def environment(home, path=None):
    inherited = {name: os.environ[name] for name in ("PATH", "TMPDIR") if name in os.environ}
    if path is not None:
        inherited["PATH"] = path
    return {**inherited, "HOME": str(home)}


def make_home(tmp_path, settings=None):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    if settings is not None:
        (home / ".claude").mkdir(exist_ok=True)
        (home / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return home


def make_repository(path, home):
    path.mkdir(parents=True)
    done = run(["git", "init", "-q"], cwd=path, env=environment(home), timeout=60.0)
    assert done.returncode == 0, done.stderr
    return path.resolve()


def install(target, home, *options, python=sys.executable, path=None):
    return run([str(python), str(INSTALLER), *options, str(target)], env=environment(home, path), timeout=120.0)


def precommit_path(target, home):
    done = run(["git", "rev-parse", "--git-path", "hooks/pre-commit"], cwd=target, env=environment(home), timeout=60.0)
    assert done.returncode == 0, done.stderr
    return target / done.stdout.strip()


def snapshot(root):
    """Every entry under root with its kind, mode and content; of .git only the hooks directory."""
    entries = {}
    for current, dirs, files in os.walk(root):
        if Path(current) == root / ".git":
            dirs[:] = [name for name in dirs if name == "hooks"]
            files[:] = []
        for name in dirs + files:
            path = Path(current) / name
            status = os.lstat(path)
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(status.st_mode):
                entries[relative] = ("link", os.readlink(path))
            elif stat.S_ISDIR(status.st_mode):
                entries[relative] = ("dir", stat.S_IMODE(status.st_mode))
            else:
                entries[relative] = ("file", stat.S_IMODE(status.st_mode), path.read_bytes())
    return entries


def kit_paths():
    found = []
    for tree in KIT_TREES:
        for current, dirs, files in os.walk(CLONE / tree):
            dirs[:] = [name for name in dirs if name != "__pycache__"]
            for name in dirs + files:
                path = Path(current) / name
                if not name.endswith(".pyc") and (path.is_symlink() or path.is_file()):
                    found.append(path.relative_to(CLONE))
    return sorted(found)


def is_executable(path):
    """The executable bit of the file itself; of the file a link resolves to, for a link."""
    return bool(os.stat(path).st_mode & stat.S_IXUSR)


def write_json(path, value, indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=indent) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def home(tmp_path):
    return make_home(tmp_path, {"sandbox": {"allowUnsandboxedCommands": False}})


@pytest.fixture
def target(tmp_path, home):
    return make_repository(tmp_path / "target", home)


@pytest.fixture
def installed(target, home):
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    return target


# T1 ---------------------------------------------------------------------------------------------------------------


def test_a_fresh_install_copies_every_kit_file_with_its_bytes_and_executable_bit(target, home):
    kit = kit_paths()
    assert [path for path in kit if (CLONE / path).is_symlink()], "the clone has no link to resolve"
    assert [path for path in kit if is_executable(CLONE / path)], "the clone has no executable to copy"
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    for path in kit:
        source, copy_ = CLONE / path, target / path
        assert not copy_.is_symlink(), f"{path} is a link"
        assert copy_.is_file(), f"{path} is not a regular file"
        assert copy_.read_bytes() == source.read_bytes(), path
        assert is_executable(copy_) == is_executable(source), path


def test_the_installed_interpreter_names_of_the_shim_are_executable_copies_of_it(installed):
    shim = installed / "tools" / "bin" / "python3"
    for name in ("python", "python3.11"):
        path = installed / "tools" / "bin" / name
        assert not path.is_symlink(), name
        assert path.is_file(), name
        assert os.access(path, os.X_OK), name
        assert path.read_bytes() == shim.read_bytes(), name


def test_a_fresh_install_writes_the_example_configuration_that_the_copied_project_config_accepts(target, home):
    assert install(target, home).returncode == 0
    assert read_json(target / ".actuarii.json") == EXAMPLE_CONFIG
    done = run([sys.executable, str(target / "tools" / "project_config.py"), "--python-script-dirs"],
               cwd=target, env=environment(home), timeout=60.0)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["."]


def test_a_fresh_install_takes_the_hooks_from_the_clone_and_writes_a_strict_sandbox(target, home):
    assert install(target, home).returncode == 0
    settings = read_json(target / ".claude" / "settings.json")
    assert set(settings) == {"hooks", "sandbox"}
    assert settings["hooks"] == CLONE_SETTINGS["hooks"]
    assert sandbox_problems(settings, EXAMPLE_CONFIG) == []
    assert (target / ".claude" / "settings.json").read_text(encoding="utf-8") == json.dumps(settings, indent=2) + "\n"


def test_a_fresh_install_adds_the_validator_server_to_mcp_json(target, home):
    assert install(target, home).returncode == 0
    assert read_json(target / ".mcp.json") == {"mcpServers": {SERVER: CLONE_SERVER}}


def test_a_fresh_install_puts_the_pre_commit_hook_where_git_reports_it(target, home):
    assert install(target, home).returncode == 0
    hook = precommit_path(target, home)
    assert hook.read_bytes() == PRE_COMMIT_SOURCE.read_bytes()
    assert os.access(hook, os.X_OK)
    assert stat.S_IMODE(os.lstat(hook).st_mode) == 0o755


def test_the_pre_commit_hook_goes_to_the_hooks_path_that_git_is_configured_with(target, home):
    done = run(["git", "config", "core.hooksPath", "custom-hooks"], cwd=target, env=environment(home), timeout=60.0)
    assert done.returncode == 0, done.stderr
    assert install(target, home).returncode == 0
    hook = target / "custom-hooks" / "pre-commit"
    assert hook.read_bytes() == PRE_COMMIT_SOURCE.read_bytes()
    assert os.access(hook, os.X_OK)
    assert precommit_path(target, home) == hook


def test_a_fresh_install_ignores_the_data_directory(target, home):
    assert install(target, home).returncode == 0
    assert (target / ".gitignore").read_text(encoding="utf-8") == ".data/\n"


def test_the_sandbox_values_of_the_installer_are_the_ones_the_settings_test_pins(target, home):
    assert install(target, home).returncode == 0
    sandbox = read_json(target / ".claude" / "settings.json")["sandbox"]
    assert {key: sandbox[key] for key in STRICT} == STRICT
    assert sandbox["filesystem"] == {"denyWrite": expected_deny_write(EXAMPLE_CONFIG)}


GIT_IDENTITY = ("-c", "user.name=Tester", "-c", "user.email=tester@example.org", "-c", "commit.gpgsign=false")
SHIM_NAMES = ("tools/bin/python", "tools/bin/python3", "tools/bin/python3.11")


def test_the_installed_kit_is_committed_with_its_own_hook_and_head_holds_the_shim_names_as_equal_executables(installed, home):
    person = environment(home, f"{Path(sys.executable).parent}:{SYSTEM_PATH}")
    added = run(["git", "add", "-A"], cwd=installed, env=person, timeout=60.0)
    assert added.returncode == 0, added.stderr
    committed = run(["git", *GIT_IDENTITY, "commit", "-q", "-m", "install the kit"], cwd=installed, env=person, timeout=120.0)
    assert committed.returncode == 0, committed.stdout + committed.stderr
    listed = run(["git", "ls-tree", "HEAD", "--", *SHIM_NAMES], cwd=installed, env=person, timeout=60.0)
    assert listed.returncode == 0, listed.stderr
    entries = {line.split("\t")[1]: line.split("\t")[0].split() for line in listed.stdout.splitlines()}
    assert sorted(entries) == sorted(SHIM_NAMES)
    assert {tuple(entry[:2]) for entry in entries.values()} == {("100755", "blob")}
    assert len({entry[2] for entry in entries.values()}) == 1


def make_clone(tmp_path):
    """A copy of what the installer reads from the clone, links kept as links, under tmp_path/clone."""
    clone = tmp_path / "clone"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for tree in KIT_TREES:
        shutil.copytree(CLONE / tree, clone / tree, symlinks=True, ignore=ignore)
    for name in ("pyproject.toml", ".mcp.json", ".claude/settings.json"):
        shutil.copy2(CLONE / name, clone / name)
    (tmp_path / "outside.txt").write_text("outside\n", encoding="utf-8")
    return clone


def install_from(clone, target, home):
    return run([sys.executable, str(clone / "tools" / "install.py"), str(target)], env=environment(home), timeout=120.0)


BAD_LINKS = [
    ("tools/linked-nowhere", "nowhere"),
    ("tools/linked-loop", "linked-loop"),
    ("tools/linked-directory", "bin"),
    (".claude/agents/linked-directory", "../skills"),
    ("tools/linked-config", "../pyproject.toml"),
    ("tools/linked-outside", "../../outside.txt"),
]


@pytest.mark.parametrize("relative, destination", BAD_LINKS, ids=[case[0] for case in BAD_LINKS])
def test_a_link_in_a_kit_tree_that_is_not_a_regular_file_inside_the_kit_trees_exits_two_names_it_and_writes_nothing(
        tmp_path, target, home, relative, destination):
    clone = make_clone(tmp_path)
    (clone / relative).symlink_to(destination)
    before = snapshot(target)
    done = install_from(clone, target, home)
    assert done.returncode == 2, done.stderr
    assert done.stderr.startswith(PREFIX)
    assert relative in done.stderr
    assert len(done.stderr.splitlines()) == 1
    assert snapshot(target) == before


def test_a_link_that_resolves_to_a_regular_file_inside_the_kit_trees_is_installed_as_a_file_with_the_bytes_and_mode_of_its_target(
        tmp_path, target, home):
    clone = make_clone(tmp_path)
    links = {
        "tools/linked.py": ("__init__.py", "tools/__init__.py"),
        ".claude/agents/linked.py": ("../../tools/__init__.py", "tools/__init__.py"),
        "tools/chained.py": ("linked.py", "tools/__init__.py"),
        "tools/linked-run": ("bin/python3", "tools/bin/python3"),
    }
    for relative, (destination, _) in links.items():
        (clone / relative).symlink_to(destination)
    done = install_from(clone, target, home)
    assert done.returncode == 0, done.stderr
    for relative, (_, resolved) in links.items():
        copy_ = target / relative
        assert not copy_.is_symlink(), relative
        assert copy_.is_file(), relative
        assert copy_.read_bytes() == (clone / resolved).read_bytes(), relative
        assert is_executable(copy_) == is_executable(clone / resolved), relative
    assert is_executable(target / "tools/linked-run")


# T2 ---------------------------------------------------------------------------------------------------------------


def hook_run(target, home, payload):
    script = target / "tools" / "hooks" / "require_boundary_validation.py"
    return run([sys.executable, str(script)], cwd=target, env=environment(home), stdin=json.dumps(payload), timeout=60.0)


def validate(target, home, proposal, target_file):
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "test", "version": "0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "validate_proposal", "arguments": {"proposal": proposal, "target_file": str(target_file)}}},
    ]
    script = target / "tools" / "boundary_validator" / "validator.py"
    done = run([sys.executable, str(script)], cwd=target, env=environment(home),
               stdin="".join(json.dumps(request) + "\n" for request in requests), timeout=60.0)
    assert done.returncode == 0, done.stderr
    responses = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]
    return json.loads(responses[-1]["result"]["content"][0]["text"])


def write_payload(target, name, content):
    return {"tool_name": "Write", "cwd": str(target), "tool_input": {"file_path": str(target / name), "content": content}}


def proposal_for(name, content):
    return {"Intent_Class": "SPEC", "Target_File": name, "Topological_Grounding": "",
            "Implementation_Block": content, "Safety_Abort": "NONE", "Rationale": "A test proposal."}


def test_before_the_validator_has_ever_run_the_installed_gate_still_denies(installed, home):
    denied = hook_run(installed, home, write_payload(installed, "AGENTS.md", "# Rules\n"))
    assert denied.returncode == 2, denied.stderr
    assert not (installed / ".data").exists()
    assert "AGENTS.md is governed by" in denied.stderr
    assert "(source: .actuarii.json)" in denied.stderr
    assert "mcp__boundary-validator__validate_proposal" in denied.stderr


def test_the_installed_kit_denies_an_unreceipted_write_and_allows_it_after_the_targets_own_receipt(installed, home):
    content = "# Rules of this repository\n"
    payload = write_payload(installed, "AGENTS.md", content)
    other = validate(installed, home, proposal_for("CLAUDE.md", "other\n"), installed / "CLAUDE.md")
    assert other["final_decision"] == "EXECUTE_SAFE", other
    assert (installed / ".data" / "boundary_validator_audit.db").is_file()
    denied = hook_run(installed, home, payload)
    assert denied.returncode == 2, denied.stderr
    assert ".actuarii.json" in denied.stderr
    assert "AGENTS.md" in denied.stderr
    decision = validate(installed, home, proposal_for("AGENTS.md", content), installed / "AGENTS.md")
    assert decision["final_decision"] == "EXECUTE_SAFE", decision
    allowed = hook_run(installed, home, payload)
    assert allowed.returncode == 0, allowed.stderr


# T3 ---------------------------------------------------------------------------------------------------------------


def settings_with(value):
    def setup(target):
        write_json(target / ".claude" / "settings.json", value)
    return setup


def raw_settings(text):
    def setup(target):
        path = target / ".claude" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
    return setup


def different_kit_file(target):
    path = target / "tools" / "project_config.py"
    path.parent.mkdir(parents=True)
    path.write_text("different\n", encoding="utf-8")


def kit_file_that_is_a_directory(target):
    (target / "tools" / "project_config.py").mkdir(parents=True)


def kit_link_that_is_a_file(target):
    path = target / "tools" / "bin" / "python"
    path.parent.mkdir(parents=True)
    path.write_text("python3\n", encoding="utf-8")


def kit_file_that_is_a_link(target):
    path = target / "tools" / "bin" / "python"
    path.parent.mkdir(parents=True)
    path.symlink_to("python3")


def tools_that_is_a_file(target):
    (target / "tools").write_text("not a directory\n", encoding="utf-8")


def different_server(target):
    write_json(target / ".mcp.json", {"mcpServers": {SERVER: {**CLONE_SERVER, "command": "other"}}})


def mcp_that_is_not_an_object(target):
    write_json(target / ".mcp.json", ["not", "an", "object"])


def different_configuration(target):
    write_json(target / ".actuarii.json", {**EXAMPLE_CONFIG, "receipt_window_seconds": 60})


def different_pre_commit(target, home=None):
    hook = target / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)


def non_executable_pre_commit(target, home=None):
    hook = target / ".git" / "hooks" / "pre-commit"
    hook.write_bytes(PRE_COMMIT_SOURCE.read_bytes())
    hook.chmod(0o644)


CONFLICTS = [
    ("a-different-kit-file", different_kit_file, "tools/project_config.py"),
    ("a-directory-where-a-kit-file-goes", kit_file_that_is_a_directory, "tools/project_config.py"),
    ("a-file-where-a-kit-link-goes", kit_link_that_is_a_file, "tools/bin/python: exists with other content"),
    ("a-link-where-a-kit-file-goes", kit_file_that_is_a_link, "tools/bin/python: exists and is not a regular file"),
    ("a-file-where-the-kit-directory-goes", tools_that_is_a_file, "tools: "),
    ("settings-that-are-not-an-object", settings_with(["not", "an", "object"]), ".claude/settings.json"),
    ("settings-with-comments", raw_settings('// a comment\n{"permissions": {}}\n'), ".claude/settings.json"),
    ("settings-with-hooks-disabled", settings_with({"disableAllHooks": True}), ".claude/settings.json"),
    ("a-loosened-sandbox-value", settings_with({"sandbox": {"allowUnsandboxedCommands": True}}), ".claude/settings.json"),
    ("a-disabled-sandbox", settings_with({"sandbox": {"enabled": False}}), ".claude/settings.json"),
    ("a-sandbox-that-is-not-an-object", settings_with({"sandbox": True}), ".claude/settings.json"),
    ("a-different-validator-entry", different_server, ".mcp.json"),
    ("an-mcp-file-that-is-not-an-object", mcp_that_is_not_an_object, ".mcp.json"),
    ("a-different-configuration", different_configuration, ".actuarii.json"),
]


@pytest.mark.parametrize("setup, needle", [case[1:] for case in CONFLICTS], ids=[case[0] for case in CONFLICTS])
def test_a_conflict_exits_one_names_it_and_leaves_the_target_untouched(target, home, setup, needle):
    setup(target)
    before = snapshot(target)
    done = install(target, home)
    assert done.returncode == 1, done.stderr
    assert done.stderr.startswith(PREFIX)
    assert needle in done.stderr
    assert snapshot(target) == before


@pytest.mark.parametrize("setup", [different_pre_commit, non_executable_pre_commit],
                         ids=["a-different-pre-commit", "a-pre-commit-that-is-not-executable"])
def test_a_conflicting_pre_commit_exits_one_and_leaves_the_git_hooks_as_they_were(target, home, setup):
    setup(target)
    before = snapshot(target)
    done = install(target, home)
    assert done.returncode == 1, done.stderr
    assert done.stderr.startswith(PREFIX)
    assert "pre-commit" in done.stderr
    assert snapshot(target) == before


def test_every_conflict_is_listed_at_once(target, home):
    different_kit_file(target)
    different_server(target)
    different_configuration(target)
    different_pre_commit(target)
    before = snapshot(target)
    done = install(target, home)
    assert done.returncode == 1, done.stderr
    for needle in ("tools/project_config.py", ".mcp.json", ".actuarii.json", "pre-commit"):
        assert needle in done.stderr, needle
    assert snapshot(target) == before


# T4 ---------------------------------------------------------------------------------------------------------------


EXISTING_SETTINGS = {
    "model": "some-model",
    "permissions": {"allow": ["Bash(ls)"], "deny": ["WebFetch"]},
    "hooks": {
        "PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo mine"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "echo stopped"}]}],
    },
    "sandbox": {
        "enabled": True,
        "network": {"allowedDomains": ["example.org"]},
        "filesystem": {"denyWrite": ["./secret", "./tools"], "allowRead": ["."]},
    },
}


def test_existing_settings_are_merged_and_not_replaced(target, home):
    existing = copy.deepcopy(EXISTING_SETTINGS)
    kit_hooks = CLONE_SETTINGS["hooks"]
    existing["hooks"]["PreToolUse"].append(kit_hooks["PreToolUse"][0])
    path = target / ".claude" / "settings.json"
    write_json(path, existing, indent=4)
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    merged = read_json(path)
    assert list(merged) == ["model", "permissions", "hooks", "sandbox"]
    assert merged["model"] == "some-model"
    assert merged["permissions"] == EXISTING_SETTINGS["permissions"]
    assert merged["hooks"]["Stop"] == EXISTING_SETTINGS["hooks"]["Stop"]
    assert merged["hooks"]["PreToolUse"] == EXISTING_SETTINGS["hooks"]["PreToolUse"] + [kit_hooks["PreToolUse"][0]] + kit_hooks["PreToolUse"][1:]
    for event, groups in kit_hooks.items():
        for group in groups:
            assert merged["hooks"][event].count(group) == 1, (event, group)
    assert list(merged["hooks"])[:2] == ["PreToolUse", "Stop"]
    sandbox = merged["sandbox"]
    assert list(sandbox)[:3] == ["enabled", "network", "filesystem"]
    assert sandbox["network"] == {"allowedDomains": ["example.org"]}
    assert {key: sandbox[key] for key in STRICT} == STRICT
    assert sandbox["filesystem"]["allowRead"] == ["."]
    kit_entries = [entry for entry in expected_deny_write(EXAMPLE_CONFIG) if entry not in ("./secret", "./tools")]
    assert sandbox["filesystem"]["denyWrite"] == ["./secret", "./tools"] + kit_entries
    assert path.read_text(encoding="utf-8") == json.dumps(merged, indent=2) + "\n"


def test_settings_that_already_hold_the_kit_are_left_as_they_are_even_if_formatted_otherwise(target, home):
    assert install(target, home).returncode == 0
    path = target / ".claude" / "settings.json"
    write_json(path, read_json(path), indent=4)
    before = path.read_bytes()
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    assert path.read_bytes() == before


def test_a_sandbox_value_equal_to_the_strict_one_is_not_a_conflict(target, home):
    write_json(target / ".claude" / "settings.json", {"sandbox": dict(STRICT)})
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    sandbox = read_json(target / ".claude" / "settings.json")["sandbox"]
    assert {key: sandbox[key] for key in STRICT} == STRICT
    assert sandbox["filesystem"] == {"denyWrite": expected_deny_write(EXAMPLE_CONFIG)}


def test_an_existing_mcp_file_keeps_its_other_servers_and_gains_ours(target, home):
    other = {"type": "stdio", "command": "node", "args": ["server.js"]}
    write_json(target / ".mcp.json", {"mcpServers": {"other": other}, "extra": 1}, indent=4)
    assert install(target, home).returncode == 0
    merged = read_json(target / ".mcp.json")
    assert list(merged) == ["mcpServers", "extra"]
    assert merged["mcpServers"] == {"other": other, SERVER: CLONE_SERVER}
    assert list(merged["mcpServers"]) == ["other", SERVER]


def test_an_mcp_file_that_already_holds_the_same_entry_is_left_as_it_is(target, home):
    path = target / ".mcp.json"
    write_json(path, {"mcpServers": {SERVER: CLONE_SERVER}}, indent=4)
    before = path.read_bytes()
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    assert path.read_bytes() == before


@pytest.mark.parametrize("existing, expected", [
    (b"node_modules/", b"node_modules/\n.data/\n"),
    (b"node_modules/\n", b"node_modules/\n.data/\n"),
    (b"", b".data/\n"),
    (b".data/\n", b".data/\n"),
    (b"build/\n/.data/\n", b"build/\n/.data/\n"),
    (b".data/*\n", b".data/*\n.data/\n"),
], ids=["no-final-newline", "final-newline", "empty", "has-data", "has-rooted-data", "has-other-pattern"])
def test_gitignore_gains_the_data_line_once_and_keeps_what_it_had(target, home, existing, expected):
    (target / ".gitignore").write_bytes(existing)
    assert install(target, home).returncode == 0
    assert (target / ".gitignore").read_bytes() == expected


def test_files_the_kit_does_not_own_and_identical_kit_files_stay_untouched(target, home):
    mine = target / "tools" / "mine.py"
    mine.parent.mkdir()
    mine.write_text("print('mine')\n", encoding="utf-8")
    same = target / "tools" / "__init__.py"
    same.write_bytes((CLONE / "tools" / "__init__.py").read_bytes())
    os.utime(same, ns=(10**9, 10**9))
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    assert mine.read_text(encoding="utf-8") == "print('mine')\n"
    assert os.stat(same).st_mtime_ns == 10**9


# T5 ---------------------------------------------------------------------------------------------------------------


def test_a_second_run_writes_nothing_and_says_there_was_nothing_to_do(target, home):
    first = install(target, home)
    assert first.returncode == 0, first.stderr
    assert "nothing to do" not in first.stdout
    after_first = snapshot(target)
    second = install(target, home)
    assert second.returncode == 0, second.stderr
    assert "nothing to do" in second.stdout
    assert snapshot(target) == after_first


def test_a_second_run_over_merged_settings_writes_nothing(target, home):
    write_json(target / ".claude" / "settings.json", EXISTING_SETTINGS)
    (target / ".gitignore").write_text("node_modules/", encoding="utf-8")
    assert install(target, home).returncode == 0
    after_first = snapshot(target)
    second = install(target, home)
    assert second.returncode == 0, second.stderr
    assert "nothing to do" in second.stdout
    assert snapshot(target) == after_first


# T6 ---------------------------------------------------------------------------------------------------------------


def test_a_dry_run_writes_nothing_and_reports_the_plan_the_real_run_then_carries_out(target, home):
    before = snapshot(target)
    dry = install(target, home, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert snapshot(target) == before
    real = install(target, home)
    assert real.returncode == 0, real.stderr
    dry_lines, real_lines = dry.stdout.splitlines(), real.stdout.splitlines()
    assert dry_lines[0] != real_lines[0]
    assert dry_lines[-1] == DRY_RUN_CLOSING
    assert dry_lines[1:-1] == real_lines[1:real_lines.index("next steps:")]
    assert dry.stderr == real.stderr
    assert snapshot(target) != before


def test_a_dry_run_prints_no_next_steps_and_a_real_run_still_prints_them(target, home):
    dry = install(target, home, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "next steps" not in dry.stdout
    assert "commit the installed files" not in dry.stdout
    assert dry.stdout.count(DRY_RUN_CLOSING) == 1
    real = install(target, home)
    assert real.returncode == 0, real.stderr
    assert DRY_RUN_CLOSING not in real.stdout
    assert "next steps:" in real.stdout
    assert "commit the installed files" in real.stdout
    assert real.stdout.splitlines()[-1].startswith("  3. open Claude Code in ")


def test_a_dry_run_reports_the_conflicts_and_the_exit_status_of_the_real_run(target, home):
    different_kit_file(target)
    different_server(target)
    before = snapshot(target)
    dry = install(target, home, "--dry-run")
    assert snapshot(target) == before
    real = install(target, home)
    assert snapshot(target) == before
    assert dry.returncode == real.returncode == 1
    assert dry.stderr == real.stderr
    assert dry.stdout == real.stdout
    assert "tools/project_config.py" in dry.stderr and ".mcp.json" in dry.stderr


def test_a_dry_run_over_an_installed_repository_says_there_is_nothing_to_do(installed, home):
    before = snapshot(installed)
    dry = install(installed, home, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "nothing to do" in dry.stdout
    assert dry.stdout.splitlines()[-1] == DRY_RUN_CLOSING
    assert snapshot(installed) == before


# T7 ---------------------------------------------------------------------------------------------------------------


def test_a_missing_target_exits_two_and_creates_nothing(tmp_path, home):
    missing = tmp_path / "missing"
    done = install(missing, home)
    assert done.returncode == 2
    assert done.stderr.startswith(PREFIX)
    assert len(done.stderr.splitlines()) == 1
    assert not missing.exists()


def test_a_file_as_target_exits_two(tmp_path, home):
    file_ = tmp_path / "file"
    file_.write_text("x", encoding="utf-8")
    done = install(file_, home)
    assert done.returncode == 2
    assert done.stderr.startswith(PREFIX)
    assert len(done.stderr.splitlines()) == 1
    assert file_.read_text(encoding="utf-8") == "x"


def test_a_directory_that_is_not_a_git_working_tree_exits_two_and_nothing_is_written(tmp_path, home):
    plain = tmp_path / "plain"
    plain.mkdir()
    before = snapshot(plain)
    done = install(plain, home)
    assert done.returncode == 2
    assert done.stderr.startswith(PREFIX)
    assert len(done.stderr.splitlines()) == 1
    assert snapshot(plain) == before == {}


def test_a_subdirectory_of_a_repository_exits_two_and_nothing_is_written(target, home):
    sub = target / "packages" / "app"
    sub.mkdir(parents=True)
    before = snapshot(target)
    done = install(sub, home)
    assert done.returncode == 2
    assert done.stderr.startswith(PREFIX)
    assert len(done.stderr.splitlines()) == 1
    assert snapshot(target) == before


def test_the_clone_itself_as_target_exits_two_and_nothing_is_written(home):
    def state():
        done = run(["git", "status", "--porcelain", "--ignored"], cwd=CLONE, env=environment(home), timeout=60.0)
        assert done.returncode == 0, done.stderr
        return done.stdout
    before = state()
    done = install(CLONE, home)
    assert done.returncode == 2
    assert done.stderr.startswith(PREFIX)
    assert len(done.stderr.splitlines()) == 1
    assert state() == before


# T8 ---------------------------------------------------------------------------------------------------------------


def directory_as_settings(home):
    (home / ".claude" / "settings.json").mkdir(parents=True)


WARNINGS = [
    ("missing", lambda tmp_path: make_home(tmp_path)),
    ("no-sandbox", lambda tmp_path: make_home(tmp_path, {"permissions": {}})),
    ("sandbox-without-the-key", lambda tmp_path: make_home(tmp_path, {"sandbox": {"enabled": True}})),
    ("allowed-unsandboxed", lambda tmp_path: make_home(tmp_path, {"sandbox": {"allowUnsandboxedCommands": True}})),
    ("not-json", lambda tmp_path: make_home_raw(tmp_path, "{not json")),
    ("not-an-object", lambda tmp_path: make_home(tmp_path, ["allowUnsandboxedCommands"])),
    ("unreadable", lambda tmp_path: make_home_directory(tmp_path)),
]


def make_home_raw(tmp_path, text):
    home = make_home(tmp_path)
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(text, encoding="utf-8")
    return home


def make_home_directory(tmp_path):
    home = make_home(tmp_path)
    directory_as_settings(home)
    return home


@pytest.mark.parametrize("make", [case[1] for case in WARNINGS], ids=[case[0] for case in WARNINGS])
def test_the_installer_warns_when_the_user_settings_do_not_forbid_unsandboxed_commands(tmp_path, make):
    user_home = make(tmp_path)
    target = make_repository(tmp_path / "target", user_home)
    before = snapshot(user_home)
    done = install(target, user_home)
    assert done.returncode == 0, done.stderr
    assert "warning" in done.stderr
    assert "allowUnsandboxedCommands" in done.stderr
    assert "settings.local.json" in done.stderr
    assert snapshot(user_home) == before


def test_the_installer_does_not_warn_when_the_user_settings_forbid_unsandboxed_commands(target, home):
    before = snapshot(home)
    done = install(target, home)
    assert done.returncode == 0, done.stderr
    assert "warning" not in done.stderr
    assert "allowUnsandboxedCommands" not in done.stderr
    assert snapshot(home) == before


# T9 ---------------------------------------------------------------------------------------------------------------


def test_the_installer_runs_under_the_system_python_with_the_same_result(tmp_path, home):
    if not SYSTEM_PYTHON.exists():
        pytest.skip(f"{SYSTEM_PYTHON} does not exist")
    reference = make_repository(tmp_path / "reference", home)
    system = make_repository(tmp_path / "system", home)
    assert install(reference, home).returncode == 0
    done = install(system, home, python=SYSTEM_PYTHON, path=SYSTEM_PATH)
    assert done.returncode == 0, done.stderr
    assert snapshot(system) == snapshot(reference)
