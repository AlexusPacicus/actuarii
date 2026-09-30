"""The boundary validator keeps its audit trail in its own database, independent of the engine.

Normative: AGENTS.md 1.3, 6.2; REMEDIATION-01 INV-1. The gate owns the location (hook_gate) and the
writer follows the path the reader resolves, so the two cannot diverge; nothing under
tools/boundary_validator imports the engine; the engine's own database carries no audit_log.
"""
import ast
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from helpers.db_factory import create_test_db

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.hook_gate import has_recent_execute_safe
from tools.boundary_validator.validator import validate_proposal
from traianus import storage

ROOT = Path(__file__).resolve().parents[2]
GATE_PACKAGE = ROOT / "tools" / "boundary_validator"
AUDIT_DB_NAME = "boundary_validator_audit.db"
LEGACY_AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    intent_class TEXT,
    target_file TEXT,
    decision TEXT NOT NULL,
    safety_abort TEXT
)
"""


def _doc_proposal(target_file: str) -> str:
    return json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target_file,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
    })


def _tables(db_path) -> set:
    with closing(sqlite3.connect(db_path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _imported_roots(path: Path) -> set:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_an_execute_safe_lands_in_the_gate_database_and_not_in_the_engine_database(isolate_db, isolate_audit_db):
    decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert hook_gate._db_path() == isolate_audit_db
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        rows = conn.execute(
            "SELECT decision FROM audit_log WHERE case_id = ?", (decision["case_id"],)
        ).fetchall()
    assert rows == [("EXECUTE_SAFE",)]
    assert has_recent_execute_safe(str(ROOT / "docs" / "x.md")) is True
    assert "audit_log" not in _tables(isolate_db)


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


def test_the_engine_no_longer_defines_the_audit_ddl():
    from traianus.storage import _storage

    assert not hasattr(storage, "AUDIT_LOG_DDL")
    assert "AUDIT_LOG_DDL" not in storage.__all__
    assert not hasattr(_storage, "AUDIT_LOG_DDL")


def test_a_test_engine_database_has_no_audit_log(tmp_path):
    db = tmp_path / "engine.db"
    create_test_db(str(db), seed="onehot")
    assert "audit_log" not in _tables(db)


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


def test_an_existing_audit_log_in_an_engine_database_survives_the_engine(tmp_path, monkeypatch):
    engine_db = tmp_path / "legacy_engine.db"
    with closing(sqlite3.connect(engine_db)) as conn, conn:
        conn.execute(LEGACY_AUDIT_LOG_DDL)
        conn.execute(
            "INSERT INTO audit_log (case_id, timestamp, intent_class, target_file, decision, safety_abort) "
            "VALUES ('c1', '2026-09-01 10:00:00', 'DOC', 'docs/x.md', 'EXECUTE_SAFE', 'NONE')"
        )

    def snapshot():
        with closing(sqlite3.connect(engine_db)) as conn:
            return (
                conn.execute("SELECT sql FROM sqlite_master WHERE name = 'audit_log'").fetchall(),
                conn.execute("SELECT * FROM audit_log ORDER BY rowid").fetchall(),
            )

    before = snapshot()
    monkeypatch.setattr(storage, "DB_PATH", str(engine_db))
    storage.init_relational_tables()
    storage.init_relational_tables()
    storage.get_current_nodes()
    assert snapshot() == before
