"""Before the audit trail exists, a governed write is denied with its rule and the call that resolves it.

In a freshly installed repository the audit database does not exist until the validator's first call. The
receipt queries of hook_gate keep raising on a missing database (an unverifiable trail), but the write hook
(tools/hooks/require_boundary_validation.py) says what is wrong: the target, the rule, its source, that there
is no audit trail yet and the validate_proposal call that creates it. A database path that exists but cannot
be used still goes to the fail-closed branch. The hook runs in process on a replaced stdin, against a
configuration that governs `src/**`; the conftest points the audit database at a file that does not exist.
"""
import io
import json
import sqlite3
import sys
from contextlib import closing

import pytest

from tools.boundary_validator.hook_gate import REPO_ROOT
from tools.hooks import require_boundary_validation

CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 60,
}
GOVERNED = str(REPO_ROOT / "src" / "a.py")
FREE = str(REPO_ROOT / "docs" / "x.md")
CALLS = [
    ("Write", {"file_path": GOVERNED, "content": "x = 1\n"}),
    ("Edit", {"file_path": GOVERNED, "old_string": "x = 1\n", "new_string": "x = 2\n"}),
    ("mcp__fs__write_file", {"path": GOVERNED}),
]
IDS = ["Write", "Edit", "unknown tool"]


@pytest.fixture
def gate(monkeypatch, config_file):
    config_file(CONFIG)

    def run(tool, tool_input):
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        return require_boundary_validation.main()

    return run


def listing(directory):
    return sorted(path.name for path in directory.iterdir())


# T1: with no audit database the denial names the rule, the source, the missing trail and the call


@pytest.mark.parametrize("tool, tool_input", CALLS, ids=IDS)
def test_with_no_audit_database_the_denial_names_the_rule_the_source_and_the_call(
        gate, capsys, isolate_audit_db, tool, tool_input):
    assert gate(tool, tool_input) == 2
    assert capsys.readouterr().err == (
        f"[require_boundary_validation] {GOVERNED} is governed by governed_paths entry \"src/**\" (source: .actuarii.json) and has no "
        f"recent EXECUTE_SAFE receipt: there is no audit trail yet ({isolate_audit_db} does not exist; the "
        "validator creates it on its first call). Call mcp__boundary-validator__validate_proposal with "
        f"target_file={GOVERNED}, then retry.\n"
    )


@pytest.mark.parametrize("tool, tool_input", CALLS, ids=IDS)
def test_with_no_audit_database_the_gate_creates_neither_a_database_nor_a_directory(
        gate, isolate_audit_db, tool, tool_input):
    before = listing(isolate_audit_db.parent)
    assert gate(tool, tool_input) == 2
    assert not isolate_audit_db.exists()
    assert listing(isolate_audit_db.parent) == before


# T2: a path that is not governed is allowed with no audit database


@pytest.mark.parametrize("tool, tool_input", [
    ("Write", {"file_path": FREE, "content": "x\n"}),
    ("Edit", {"file_path": FREE, "old_string": "a", "new_string": "b"}),
    ("mcp__fs__write_file", {"path": FREE}),
], ids=IDS)
def test_with_no_audit_database_a_path_that_is_not_governed_is_allowed(gate, isolate_audit_db, tool, tool_input):
    assert gate(tool, tool_input) == 0
    assert not isolate_audit_db.exists()


# T3: a database path that exists but cannot be used still denies fail-closed


def make_directory(path):
    path.mkdir()


def make_text_file(path):
    path.write_text("this is not a SQLite database\n" * 20, encoding="utf-8")


def make_database_without_audit_log(path):
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE unrelated (id INTEGER)")


@pytest.mark.parametrize("make", [make_directory, make_text_file, make_database_without_audit_log],
                         ids=["directory", "not SQLite", "no audit_log table"])
@pytest.mark.parametrize("tool, tool_input", CALLS, ids=IDS)
def test_an_audit_database_that_exists_but_cannot_be_used_denies_fail_closed(
        gate, capsys, isolate_audit_db, make, tool, tool_input):
    make(isolate_audit_db)
    assert gate(tool, tool_input) == 2
    err = capsys.readouterr().err
    assert err.startswith(
        "[require_boundary_validation] fail-closed: could not verify the boundary-validator audit trail (")
    assert "no audit trail yet" not in err
