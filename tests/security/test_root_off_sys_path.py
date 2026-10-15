"""The kit's scripts put the repository root on sys.path only to import `tools`, and take it off at once (A31).

A script that kept the root first on sys.path loaded a file of the root named like a standard-library module
(`logging.py`, `inspect.py`, `dataclasses.py`) in place of the real one, whenever it imported that module after the
insert: the gates failed closed or the validator did not start, although nobody attacked.

Every case runs a script of a copy of the kit under tmp_path, as a program with the interpreter the tests run under,
never on the real repository root, where the live hooks of the session would load whatever is planted. Each planted
module appends its name to a witness file outside the copy and then loads the real module, so a script that imports it
still works: what a case checks is which modules a script imported, which entries sys.path held when it ended, and
that it decides the same with and without them.
"""
import json
import os
import shutil
import sys
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.audit.run_process import run

CLONE = Path(__file__).resolve().parents[2]
KIT_TREES = ("tools", ".claude/agents", ".claude/skills")
KIT_FILES = ("pyproject.toml", ".mcp.json", ".claude/settings.json")
STANDARD = ("dataclasses", "sqlite3", "logging", "ast", "inspect", "subprocess")
INHERITED = {name: os.environ[name] for name in ("PATH", "TMPDIR") if name in os.environ}
PING = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
PING_ANSWER = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}) + "\n"
PATTERN = textwrap.dedent("""\
    if str(REPO_ROOT) in sys.path:
        import tools
    else:
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import tools
        finally:
            sys.path.remove(str(REPO_ROOT))
    """).splitlines()

SHADOW = """\
import importlib
import os
import sys

with open({witness!r}, "a", encoding="utf-8") as seen:
    seen.write({name!r} + "\\n")
saved = list(sys.path)
del sys.modules[{name!r}]
sys.path[:] = [entry for entry in saved if os.path.abspath(entry) != {root!r}]
real = importlib.import_module({name!r})
sys.path[:] = saved
sys.modules[{name!r}] = real
"""
FOREIGN_TOOLS = """\
with open({witness!r}, "a", encoding="utf-8") as seen:
    seen.write("tools\\n")
"""
SPY = """\
import atexit
import sys


def record():
    with open({paths!r}, "w", encoding="utf-8") as out:
        out.write("\\n".join(sys.path))


atexit.register(record)
"""
BROKEN_TOOLS = 'raise RuntimeError("tools is broken")\n'
REMOVES_ROOT = """\
import sys

sys.path[:] = [entry for entry in sys.path if entry != {root!r}]
"""


@dataclass(frozen=True)
class Script:
    id: str
    path: str
    code: int
    says: str
    arguments: tuple[str, ...] = ()
    stdin: Callable[[Path], str] | None = None


def edit_input(root):
    edit = {"file_path": str(root / "AGENTS.md"), "old_string": "a", "new_string": "b"}
    return json.dumps({"tool_name": "Edit", "tool_input": edit})


def ping_input(root):
    return PING


VALIDATOR = Script("validator", "tools/boundary_validator/validator.py", 0, PING_ANSWER, stdin=ping_input)
SCRIPTS = [
    Script("boundary", "tools/hooks/require_boundary_validation.py", 2, "no recent EXECUTE_SAFE receipt",
           stdin=edit_input),
    Script("contract", "tools/hooks/require_contract_context.py", 0, "", stdin=edit_input),
    Script("announce", "tools/hooks/announce_governance.py", 0, "actuarii: the governance rules come from"),
    Script("commit-integrity", "tools/git/commit_integrity.py", 0, ""),
    Script("commit-record", "tools/git/commit_record.py", 0, "", arguments=("{target}/COMMIT_EDITMSG",)),
    VALIDATOR,
    Script("install", "tools/install.py", 0, "dry run: nothing was written", arguments=("--dry-run", "{target}")),
    Script("review-package", "tools/audit/build_review_package.py", 0, "usage:", arguments=("--help",)),
    Script("delegation-contract", "tools/audit/delegation_contract.py", 0, "usage:", arguments=("--help",)),
    Script("verify-red-green", "tools/audit/verify_red_green.py", 0, "usage:", arguments=("--help",)),
]
HANDLERS = {
    "boundary": (2, "[require_boundary_validation] fail-closed: the boundary gate could not be imported"),
    "contract": (2, "[require_contract_context] fail-closed: the project configuration could not be imported"),
    "announce": (0, "actuarii: the project configuration could not be imported"),
    "commit-integrity": (1, "[commit_integrity] cannot start"),
    "commit-record": (1, "[commit_record] cannot start"),
}
SCRIPT = pytest.mark.parametrize("script", SCRIPTS, ids=lambda script: script.id)
GUARDED = pytest.mark.parametrize(
    "script", [script for script in SCRIPTS if script.id in HANDLERS], ids=lambda script: script.id)


@dataclass(frozen=True)
class Kit:
    root: Path
    home: Path
    target: Path
    witness: Path
    paths: Path


def environment(home, **extra):
    return {**INHERITED, "HOME": str(home), **extra}


@pytest.fixture
def kit(tmp_path):
    """A copy of the kit as the working tree has it, a git repository, and an empty git repository as a target."""
    root, home, target = tmp_path / "kit", tmp_path / "home", tmp_path / "target"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for tree in KIT_TREES:
        shutil.copytree(CLONE / tree, root / tree, symlinks=True, ignore=ignore)
    for name in KIT_FILES:
        shutil.copy2(CLONE / name, root / name)
    (root / "AGENTS.md").write_text("rules\n", encoding="utf-8")
    home.mkdir()
    target.mkdir()
    for repository in (root, target):
        done = run(["git", "init", "-q"], cwd=repository, env=environment(home), timeout=60.0)
        assert done.returncode == 0, done.stderr
    return Kit(root.resolve(), home, target.resolve(), tmp_path / "witness.txt", tmp_path / "sys_path.txt")


def launch(script, kit, **extra):
    arguments = [argument.format(target=kit.target) for argument in script.arguments]
    stdin = "" if script.stdin is None else script.stdin(kit.root)
    return run([sys.executable, str(kit.root / script.path), *arguments], cwd=kit.root,
               env=environment(kit.home, **extra), stdin=stdin, timeout=120.0)


def outcome(done):
    return done.returncode, done.stdout, done.stderr


def shadow(kit, name):
    return SHADOW.format(witness=str(kit.witness), name=name, root=str(kit.root))


def plant(kit, names=STANDARD, packages=()):
    for name in names:
        (kit.root / f"{name}.py").write_text(shadow(kit, name), encoding="utf-8")
    for name in packages:
        (kit.root / name).mkdir()
        (kit.root / name / "__init__.py").write_text(shadow(kit, name), encoding="utf-8")


def imported(kit):
    return kit.witness.read_text(encoding="utf-8").split() if kit.witness.exists() else []


@SCRIPT
def test_no_script_imports_a_module_planted_at_the_root(script, kit):
    plant(kit)
    done = launch(script, kit)
    assert imported(kit) == []
    assert done.returncode == script.code, done.stderr


@SCRIPT
@pytest.mark.parametrize("present", [False, True], ids=["absent", "present"])
def test_a_script_ends_with_the_root_on_sys_path_only_if_it_was_there(script, present, kit, tmp_path):
    spy = tmp_path / "spy"
    spy.mkdir()
    (spy / "sitecustomize.py").write_text(SPY.format(paths=str(kit.paths)), encoding="utf-8")
    entries = [str(spy), *([str(kit.root)] if present else [])]
    launch(script, kit, PYTHONPATH=os.pathsep.join(entries))
    ended = kit.paths.read_text(encoding="utf-8").splitlines()
    assert ended.count(str(kit.root)) == (1 if present else 0), ended


def test_the_validator_imports_logging_and_pydantic_off_the_root_and_the_kits_tools_over_a_foreign_one(kit, tmp_path):
    foreign = tmp_path / "foreign" / "tools"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text(FOREIGN_TOOLS.format(witness=str(kit.witness)), encoding="utf-8")
    plant(kit, ("logging",), packages=("pydantic",))
    done = launch(VALIDATOR, kit, PYTHONPATH=str(foreign.parent))
    assert imported(kit) == []
    assert (done.returncode, done.stdout) == (0, PING_ANSWER), done.stderr


@SCRIPT
def test_the_script_carries_the_same_lines_for_the_root(script):
    lines = (CLONE / script.path).read_text(encoding="utf-8").splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == PATTERN[0]]
    assert len(starts) == 1, "the lines for the root are not there exactly once"
    block = textwrap.dedent("\n".join(lines[starts[0]:starts[0] + len(PATTERN)]))
    assert block.splitlines() == PATTERN
    assert sum("sys.path.insert" in line for line in lines) == 1


@SCRIPT
def test_a_script_decides_the_same_with_and_without_planted_modules(script, kit):
    clean = launch(script, kit)
    assert clean.returncode == script.code, clean.stderr
    assert script.says in clean.stdout + clean.stderr
    plant(kit)
    assert outcome(launch(script, kit)) == outcome(clean)


@GUARDED
def test_a_hook_whose_tools_cannot_be_imported_ends_in_its_handler(script, kit):
    (kit.root / "tools" / "__init__.py").write_text(BROKEN_TOOLS, encoding="utf-8")
    done = launch(script, kit)
    code, says = HANDLERS[script.id]
    assert done.returncode == code, done.stderr
    assert says in done.stdout + done.stderr


@GUARDED
def test_a_hook_whose_root_cannot_be_removed_ends_in_its_handler(script, kit):
    (kit.root / "tools" / "__init__.py").write_text(REMOVES_ROOT.format(root=str(kit.root)), encoding="utf-8")
    done = launch(script, kit)
    code, says = HANDLERS[script.id]
    assert done.returncode == code, done.stderr
    assert says in done.stdout + done.stderr
