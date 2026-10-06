"""The boundary validator keeps its audit trail in its own database, independent of the engine.

Normative: REMEDIATION-01 INV-1. The gate owns the location (hook_gate) and the
writer follows the path the reader resolves, so the two cannot diverge; nothing under
tools/boundary_validator imports the engine.
"""
import ast
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.hook_gate import has_recent_execute_safe
from tools.boundary_validator.validator import validate_proposal

ROOT = Path(__file__).resolve().parents[2]
GATE_PACKAGE = ROOT / "tools" / "boundary_validator"
AUDIT_DB_NAME = "boundary_validator_audit.db"


def _doc_proposal(target_file: str) -> str:
    return json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target_file,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
    })


def _imported_roots(path: Path) -> set:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_an_execute_safe_lands_in_the_gate_database(isolate_audit_db):
    decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert hook_gate._db_path() == isolate_audit_db
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        rows = conn.execute(
            "SELECT decision FROM audit_log WHERE case_id = ?", (decision["case_id"],)
        ).fetchall()
    assert rows == [("EXECUTE_SAFE",)]
    assert has_recent_execute_safe(str(ROOT / "docs" / "x.md")) is True


def test_the_default_audit_database_is_anchored_at_the_repo_root_whatever_the_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", hook_gate.DEFAULT_AUDIT_DB)
    monkeypatch.chdir(tmp_path)
    expected = ROOT / ".data" / AUDIT_DB_NAME
    assert hook_gate.DEFAULT_AUDIT_DB == expected
    assert hook_gate._db_path() == expected


def test_the_validator_writes_to_the_path_the_gate_resolves_and_creates_what_is_missing(tmp_path, monkeypatch):
    target = tmp_path / "not" / "yet" / AUDIT_DB_NAME
    monkeypatch.setattr(hook_gate, "_db_path", lambda: target)
    validator._persist_audit("case-w", "EXECUTE_SAFE", "DOC", "docs/x.md", "NONE")
    with closing(sqlite3.connect(target)) as conn:
        assert conn.execute("SELECT case_id, decision FROM audit_log").fetchall() == [("case-w", "EXECUTE_SAFE")]


def test_a_repointed_gate_attribute_moves_the_writer_and_the_reader_together(tmp_path, monkeypatch):
    repointed = tmp_path / "repointed" / AUDIT_DB_NAME
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", repointed)
    decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert repointed.exists()
    assert hook_gate._db_path() == repointed
    assert has_recent_execute_safe(str(ROOT / "docs" / "x.md")) is True


def test_during_the_suite_the_audit_database_is_under_the_tests_tmp_path(tmp_path):
    assert hook_gate._db_path() == tmp_path / AUDIT_DB_NAME
    assert hook_gate._db_path() != hook_gate.DEFAULT_AUDIT_DB


@pytest.mark.parametrize("module", sorted(GATE_PACKAGE.rglob("*.py")), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_module_of_the_gate_imports_the_engine(module):
    assert "traianus" not in _imported_roots(module)


def test_the_gate_fails_closed_when_the_audit_table_is_missing(tmp_path, monkeypatch):
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", empty)
    with pytest.raises(sqlite3.Error):
        has_recent_execute_safe(str(ROOT / "AGENTS.md"))


def test_the_validator_fails_open_when_the_audit_database_cannot_be_written(tmp_path, monkeypatch):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path)
    decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"
