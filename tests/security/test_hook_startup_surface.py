"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Startup surface of the PreToolUse gate (AGENTS.md 6.2): the harness spawns
the hook in an ambient environment we do not control -- PATH, cwd and
installed packages all differ from a developer shell. An interpreter without
the substrate's third-party dependencies MUST still reach the gate logic, so
`traianus/security/hook_gate.py` MUST import nothing outside the standard
library, and the hook script MUST turn an unusable gate into exit code 2
(block) instead of an unhandled traceback -- exit 1 reads to the harness as a
failed hook, not as a denial, and the edit goes through.

The gate also MUST resolve its database to an absolute path and MUST NOT
create one: a relative path makes the decision depend on cwd, and a gate that
creates its own empty audit trail would litter a stray database wherever the
harness happened to run it.

Normative: AGENTS.md 1.3, 6.2
Coverage: SEC-M-13"""
import ast
import sqlite3
import sys
from pathlib import Path

import pytest

from traianus import storage
from traianus.security import hook_gate

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "traianus" / "security" / "hook_gate.py"
HOOK = ROOT / "tools" / "hooks" / "require_boundary_validation.py"
STORAGE_INIT = ROOT / "traianus" / "storage" / "__init__.py"

GATE_MODULE = "traianus.security.hook_gate"


def _import_time_statements(body):
    """Statements that run when the module is imported: the top level plus
    the bodies of try/if/with, but never a function or class body."""
    for node in body:
        yield node
        if isinstance(node, (ast.Try, ast.If, ast.With)):
            nested = list(node.body)
            nested += [s for h in getattr(node, "handlers", []) for s in h.body]
            nested += list(getattr(node, "orelse", []))
            nested += list(getattr(node, "finalbody", []))
            yield from _import_time_statements(nested)


def _imported_roots(path: Path) -> set:
    """Root package names imported at import time -- the ones that decide
    whether the interpreter ever reaches main()."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in _import_time_statements(tree.body):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _declared_db_name() -> str:
    tree = ast.parse(STORAGE_INIT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DB_PATH"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("traianus/storage/__init__.py declares no DB_PATH")


def _handler_exits_with_two(node: ast.Try) -> bool:
    for handler in node.handlers:
        for statement in ast.walk(handler):
            if (
                isinstance(statement, ast.Call)
                and isinstance(statement.func, ast.Attribute)
                and statement.func.attr == "exit"
                and any(
                    isinstance(arg, ast.Constant) and arg.value == 2
                    for arg in statement.args
                )
            ):
                return True
    return False


def test_security_gate_imports_only_the_standard_library():
    """hook_gate MUST start under any interpreter, including one that has
    never installed the substrate's third-party dependencies."""
    foreign = _imported_roots(GATE) - set(sys.stdlib_module_names)
    assert not foreign, (
        f"hook_gate.py imports {sorted(foreign)} at import time; a gate that "
        "needs the substrate installed cannot run where the harness spawns it"
    )


def test_security_hook_script_imports_only_stdlib_and_the_gate():
    foreign = _imported_roots(HOOK) - set(sys.stdlib_module_names) - {"traianus"}
    assert not foreign, f"the hook script imports {sorted(foreign)}"


def test_security_hook_script_turns_an_unusable_gate_into_a_block():
    """The gate import MUST sit inside a try whose handler exits 2. An
    unhandled ImportError exits 1, which the harness reads as a broken hook
    and not as a denial -- the fail-closed posture would invert silently."""
    tree = ast.parse(HOOK.read_text(encoding="utf-8"))
    guarded = [
        node
        for node in tree.body
        if isinstance(node, ast.Try)
        and any(
            isinstance(inner, ast.ImportFrom) and inner.module == GATE_MODULE
            for inner in ast.walk(node)
        )
    ]
    assert guarded, f"the import of {GATE_MODULE} is not guarded by a try"
    assert any(_handler_exits_with_two(node) for node in guarded), (
        "the guard must exit 2 (block), not fall through or exit 1"
    )


def test_security_gate_default_db_name_matches_the_substrate():
    """The gate cannot import the storage package, so it carries its own copy
    of the database name; the copy MUST agree with the declaration."""
    assert hook_gate.DEFAULT_DB_NAME == _declared_db_name()


def test_security_gate_db_path_is_absolute():
    """A relative path would make the decision depend on the cwd the harness
    happens to spawn the hook with."""
    assert hook_gate._db_path().is_absolute()


def test_security_gate_follows_the_active_substrate_db_path(tmp_path, monkeypatch):
    """When the substrate is already imported (tests, tools), the gate MUST
    read the same database the validator writes to."""
    active = tmp_path / "active.db"
    monkeypatch.setattr(storage, "DB_PATH", str(active))
    assert hook_gate._db_path() == active


def test_security_gate_never_creates_a_database(tmp_path, monkeypatch):
    """A missing audit trail is an unverifiable one: the gate MUST fail so the
    caller blocks, and MUST NOT leave an empty database behind."""
    missing = tmp_path / "absent.db"
    monkeypatch.setattr(storage, "DB_PATH", str(missing))
    with pytest.raises(sqlite3.Error):
        hook_gate.has_recent_execute_safe(str(ROOT / "AGENTS.md"))
    assert not missing.exists()
