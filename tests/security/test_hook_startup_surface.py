"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Startup surface of the PreToolUse gate: the harness spawns
the hook in an ambient environment we do not control -- PATH, cwd and
installed packages all differ from a developer shell. An interpreter without
the substrate's third-party dependencies MUST still reach the gate logic, so
`tools/boundary_validator/hook_gate.py` MUST import nothing outside the standard
library, and the hook script MUST turn an unusable gate into exit code 2
(block) instead of an unhandled traceback -- exit 1 reads to the harness as a
failed hook, not as a denial, and the edit goes through.

The gate also MUST resolve its database to an absolute path and MUST NOT
create one: a relative path makes the decision depend on cwd, and a gate that
creates its own empty audit trail would litter a stray database wherever the
harness happened to run it.

Normative: the fail-closed startup of the PreToolUse gate
Coverage: SEC-M-13"""
import ast
import sqlite3
import sys
from pathlib import Path

import pytest

from tools.boundary_validator import hook_gate

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "boundary_validator" / "hook_gate.py"
HOOK = ROOT / "tools" / "hooks" / "require_boundary_validation.py"
PROJECT_CONFIG = ROOT / "tools" / "project_config.py"
PRIMITIVES = ROOT / "tools" / "boundary_validator" / "primitives.py"

GATE_MODULE = "tools.boundary_validator.hook_gate"
PRIMITIVES_MODULE = "tools.boundary_validator.primitives"
GATE_DEPENDENCY = "tools.project_config"


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


def _foreign_imports(path: Path) -> set:
    """Dotted names imported at import time from outside the standard library;
    `from tools import x` counts as `tools.x`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    foreign = set()
    for node in _import_time_statements(tree.body):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [f"{node.module}.{alias.name}" if node.module == "tools" else node.module
                     for alias in node.names]
        else:
            continue
        foreign.update(name for name in names if name.split(".")[0] not in sys.stdlib_module_names)
    return foreign


def _postpones_annotations(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
    return any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def test_security_gate_imports_only_the_standard_library_and_the_project_configuration():
    """hook_gate MUST start under any interpreter, including one that has
    never installed the substrate's third-party dependencies; the project
    configuration it reads is the one module it may add."""
    foreign = _foreign_imports(GATE) - {GATE_DEPENDENCY}
    assert not foreign, (
        f"hook_gate.py imports {sorted(foreign)} at import time; a gate that "
        "needs the substrate installed cannot run where the harness spawns it"
    )


def test_security_project_configuration_imports_only_the_standard_library():
    foreign = _imported_roots(PROJECT_CONFIG) - set(sys.stdlib_module_names)
    assert not foreign, (
        f"project_config.py imports {sorted(foreign)} at import time; the gate "
        "imports it, so a broken import there opens the gate"
    )


@pytest.mark.parametrize(
    "path", [GATE, PROJECT_CONFIG, PRIMITIVES, HOOK], ids=["gate", "project_config", "primitives", "hook"]
)
def test_security_gate_modules_postpone_annotations_for_a_system_python_3_9(path):
    assert _postpones_annotations(path)


def test_security_hook_script_imports_only_stdlib_and_the_gate():
    foreign = _imported_roots(HOOK) - set(sys.stdlib_module_names) - {"tools"}
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


def test_security_primitives_module_imports_only_the_standard_library():
    """The hook imports it at start: a third-party import there would stop the gate before it decides."""
    tree = ast.parse(PRIMITIVES.read_text(encoding="utf-8"), feature_version=(3, 9))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "primitives.py must not import a relative module"
            roots.add(node.module.split(".")[0])
    assert roots, "primitives.py imports nothing, not even ast"
    assert not roots - set(sys.stdlib_module_names), sorted(roots - set(sys.stdlib_module_names))


def test_security_hook_script_imports_the_primitives_inside_its_fail_closed_try():
    tree = ast.parse(HOOK.read_text(encoding="utf-8"))
    guarded = [
        node
        for node in tree.body
        if isinstance(node, ast.Try)
        and any(
            isinstance(inner, ast.ImportFrom) and inner.module == PRIMITIVES_MODULE
            for inner in ast.walk(node)
        )
    ]
    assert guarded, f"the import of {PRIMITIVES_MODULE} is not guarded by a try"
    assert any(_handler_exits_with_two(node) for node in guarded)
    assert any(
        isinstance(inner, ast.ImportFrom) and inner.module == GATE_MODULE
        for node in guarded
        for inner in ast.walk(node)
    ), "the primitives and the gate must share the one guarded import"


def test_security_gate_db_path_is_absolute():
    """A relative path would make the decision depend on the cwd the harness
    happens to spawn the hook with."""
    assert hook_gate.DEFAULT_AUDIT_DB.is_absolute()
    assert hook_gate._db_path().is_absolute()


def test_security_gate_never_creates_a_database(tmp_path, monkeypatch):
    """A missing audit trail is an unverifiable one: the gate MUST fail so the
    caller blocks, and MUST NOT leave an empty database behind."""
    missing = tmp_path / "absent.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", missing)
    with pytest.raises(sqlite3.Error):
        hook_gate.has_recent_execute_safe(str(ROOT / "AGENTS.md"))
    assert not missing.exists()
