"""A receipt binds the exact change, not only the file (audit A04).

validate_proposal keeps, for every EXECUTE_SAFE, the SHA-256 of the UTF-8 bytes of its Topological_Grounding
and of its Implementation_Block in the `receipts` table of the audit database. The write gate
(tools/hooks/require_boundary_validation.py) lets a known writer through on a governed path only when a recent
receipt matches what that tool writes: Edit its old_string and new_string, MultiEdit each of its edits, Write
its content (any citation), NotebookEdit its new_source (any citation). Class 3 tools keep the receipt per
file. The tests run in process: the real validator, the real hook on a replaced stdin, the audit database the
conftest isolates, and a configuration that governs `src/**` with a window of 60 seconds.
"""
import hashlib
import io
import json
import sqlite3
import sys
from contextlib import closing

import pytest

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.hook_gate import REPO_ROOT
from tools.boundary_validator.validator import validate_proposal
from tools.hooks import require_boundary_validation

CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 60,
}
TARGET = "src/a.py"
GOVERNED = str(REPO_ROOT / "src" / "a.py")
OLD = "old = 1\n"
NEW = "new = 2\n"
UNKNOWN = "mcp__fs__write_file"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def proposal(target=TARGET, grounding=OLD, block=NEW, intent="DOC", abort="NONE"):
    return json.dumps({
        "Intent_Class": intent,
        "Target_File": target,
        "Topological_Grounding": grounding,
        "Implementation_Block": block,
        "Safety_Abort": abort,
    })


def grant(target=TARGET, grounding=OLD, block=NEW):
    decision = validate_proposal(proposal(target, grounding, block), target)
    assert decision["final_decision"] == "EXECUTE_SAFE"
    return decision


def receipts(db):
    with closing(sqlite3.connect(db)) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'receipts'").fetchone():
            return []
        return conn.execute(
            "SELECT case_id, target_file, grounding_sha256, block_sha256 FROM receipts"
        ).fetchall()


def age(db, seconds):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE receipts SET timestamp = datetime('now', ?)", (f"-{seconds} seconds",))


def edit(old=OLD, new=NEW, **extra):
    return "Edit", {"file_path": GOVERNED, "old_string": old, "new_string": new, **extra}


def multi_edit(*pairs):
    return "MultiEdit", {"file_path": GOVERNED,
                         "edits": [{"old_string": old, "new_string": new} for old, new in pairs]}


def write(content=NEW):
    return "Write", {"file_path": GOVERNED, "content": content}


def notebook(new_source=NEW):
    return "NotebookEdit", {"notebook_path": GOVERNED, "new_source": new_source}


@pytest.fixture
def gate(monkeypatch, config_file):
    config_file(CONFIG)

    def run(call):
        tool, tool_input = call
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        return require_boundary_validation.main()

    return run


# T1: every EXECUTE_SAFE leaves a receipt with the hashes of the exact quote and block, and nothing else does


def test_an_execute_safe_leaves_a_receipt_with_the_case_the_file_and_the_two_hashes(isolate_audit_db):
    decision = grant(TARGET, OLD, NEW)
    assert receipts(isolate_audit_db) == [(decision["case_id"], TARGET, sha(OLD), sha(NEW))]
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert conn.execute("SELECT case_id, decision FROM audit_log").fetchall() == [
            (decision["case_id"], "EXECUTE_SAFE")]


def test_the_receipt_keeps_the_target_file_as_it_arrived(isolate_audit_db):
    grant(GOVERNED)
    [(_case, target, _g, _b)] = receipts(isolate_audit_db)
    assert target == GOVERNED


@pytest.mark.parametrize("grounding, block", [
    ("a b", "x"),
    ("a  b", "x"),
    ("a\nb", "x"),
    ("a\r\nb", "x"),
    ("q", "x"),
    ("q", "x "),
    ("q", "x\n"),
    ("q", ""),
    ("", "x"),
    ("é", "x"),
    ("é", "x"),
    ("q", "é"),
    ("q", "é"),
    ("q", "# ☃ \U0001f600"),
])
def test_the_hashes_are_those_of_the_exact_utf8_bytes_with_nothing_normalised(isolate_audit_db, grounding, block):
    grant(TARGET, grounding, block)
    [(_case, _target, grounding_sha, block_sha)] = receipts(isolate_audit_db)
    assert grounding_sha == hashlib.sha256(grounding.encode("utf-8")).hexdigest()
    assert block_sha == hashlib.sha256(block.encode("utf-8")).hexdigest()


def test_two_texts_that_differ_by_one_byte_leave_two_different_hashes(isolate_audit_db):
    grant(TARGET, "a\nb", NEW)
    grant(TARGET, "a\r\nb", NEW)
    first, second = receipts(isolate_audit_db)
    assert first[2] != second[2]
    assert first[3] == second[3]


@pytest.mark.parametrize("text, target", [
    pytest.param(proposal(abort="BOUNDARY_VIOLATION"), TARGET, id="safety-abort"),
    pytest.param("{not json", TARGET, id="invalid-json"),
    pytest.param(proposal(target="src/b.py"), TARGET, id="target-mismatch"),
    pytest.param(proposal(target="tools/boundary_validator/hook_gate.py", grounding="not in that file", intent="FIX"),
                 "tools/boundary_validator/hook_gate.py", id="grounding-failure"),
])
def test_a_decision_other_than_execute_safe_leaves_no_receipt(isolate_audit_db, text, target):
    assert validate_proposal(text, target)["final_decision"] != "EXECUTE_SAFE"
    assert receipts(isolate_audit_db) == []


@pytest.mark.parametrize("grounding, block", [("\ud800", NEW), (OLD, "\udfff")], ids=["quote", "block"])
def test_text_that_cannot_be_hashed_is_not_an_execute_safe(isolate_audit_db, grounding, block):
    assert validate_proposal(proposal(grounding=grounding, block=block), TARGET)["final_decision"] != "EXECUTE_SAFE"
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert conn.execute("SELECT case_id FROM audit_log WHERE decision = 'EXECUTE_SAFE'").fetchall() == []
    assert receipts(isolate_audit_db) == []


def test_the_receipt_table_is_in_the_database_the_gate_resolves(isolate_audit_db):
    grant()
    assert hook_gate._db_path() == isolate_audit_db
    assert len(receipts(isolate_audit_db)) == 1


def test_a_receipt_that_cannot_be_written_leaves_the_validator_total_and_the_write_denied(isolate_audit_db, gate):
    with closing(sqlite3.connect(isolate_audit_db)) as conn, conn:
        conn.execute("CREATE TABLE receipts (unrelated TEXT)")
    decision = validate_proposal(proposal(), TARGET)
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert gate(edit()) == 2


# T2: a known writer passes only with a receipt for its exact content


def test_an_edit_with_the_receipt_for_its_old_and_new_string_passes(gate):
    grant(TARGET, OLD, NEW)
    assert gate(edit()) == 0


def test_a_write_with_a_receipt_for_its_content_passes_whatever_the_citation(gate):
    grant(TARGET, "any quote at all", NEW)
    assert gate(write(NEW)) == 0


def test_a_notebook_edit_with_a_receipt_for_its_new_source_passes_whatever_the_citation(gate):
    grant(TARGET, "", NEW)
    assert gate(notebook(NEW)) == 0


def test_a_notebook_edit_that_deletes_a_cell_needs_the_receipt_for_the_empty_source(gate):
    call = ("NotebookEdit", {"notebook_path": GOVERNED, "cell_id": "c1", "edit_mode": "delete"})
    grant(TARGET, "", NEW)
    assert gate(call) == 2
    grant(TARGET, "", "")
    assert gate(call) == 0


def test_a_multi_edit_passes_when_every_edit_has_its_receipt(gate):
    grant(TARGET, "one", "uno")
    grant(TARGET, "two", "dos")
    assert gate(multi_edit(("one", "uno"), ("two", "dos"))) == 0


def test_a_multi_edit_with_one_edit_without_a_receipt_is_denied(gate):
    grant(TARGET, "one", "uno")
    assert gate(multi_edit(("one", "uno"), ("two", "dos"))) == 2


def test_a_receipt_is_not_consumed_by_the_write_it_allows(gate):
    grant(TARGET, OLD, NEW)
    assert gate(edit()) == 0
    assert gate(edit()) == 0


def test_replace_all_does_not_change_what_an_edit_needs(gate):
    grant(TARGET, OLD, NEW)
    assert gate(edit(replace_all=True)) == 0
    assert gate(edit(old="other", replace_all=True)) == 2


@pytest.mark.parametrize("old, new", [
    ("other", NEW),
    (OLD, "other"),
    ("other", "other"),
    (OLD + " ", NEW),
    (OLD, NEW + " "),
    (OLD.replace("\n", "\r\n"), NEW),
    (OLD, NEW.replace("\n", "\r\n")),
    (OLD, NEW.rstrip("\n")),
    (OLD, ""),
    ("", NEW),
])
def test_an_edit_with_other_content_than_the_receipt_is_denied_down_to_one_byte(gate, old, new):
    grant(TARGET, OLD, NEW)
    assert gate(edit(old, new)) == 2


def test_an_edit_whose_new_string_matches_a_receipt_with_another_old_string_is_denied(gate):
    grant(TARGET, "first", NEW)
    grant(TARGET, OLD, "second")
    assert gate(edit(OLD, NEW)) == 2


@pytest.mark.parametrize("content", ["other", NEW + " ", NEW.replace("\n", "\r\n"), "", "rmtree"])
def test_a_write_with_other_content_than_the_receipt_is_denied(gate, content):
    grant(TARGET, "q", NEW)
    assert gate(write(content)) == 2


@pytest.mark.parametrize("source", ["other", NEW + " ", NEW.replace("\n", "\r\n"), ""])
def test_a_notebook_edit_with_another_new_source_than_the_receipt_is_denied(gate, source):
    grant(TARGET, "q", NEW)
    assert gate(notebook(source)) == 2


def test_a_receipt_for_another_file_with_the_same_content_does_not_count(gate):
    grant("src/b.py", OLD, NEW)
    assert gate(edit()) == 2


def test_a_receipt_older_than_the_window_does_not_count(isolate_audit_db, gate):
    grant(TARGET, OLD, NEW)
    age(isolate_audit_db, 120)
    assert gate(edit()) == 2
    age(isolate_audit_db, 30)
    assert gate(edit()) == 0


def test_an_expired_receipt_does_not_count_for_a_write_or_a_notebook_edit(isolate_audit_db, gate):
    grant(TARGET, "q", NEW)
    age(isolate_audit_db, 120)
    assert gate(write()) == 2
    assert gate(notebook()) == 2


def test_the_receipt_is_matched_by_file_identity_not_by_spelling(gate):
    grant("src/../src/a.py", OLD, NEW)
    assert gate(edit()) == 0


def test_an_ungoverned_path_needs_neither_a_receipt_nor_content(gate):
    free = str(REPO_ROOT / "docs" / "x.md")
    assert gate(("Edit", {"file_path": free})) == 0
    assert gate(("Write", {"file_path": free})) == 0


# a content field that is not text, or an edit list that is not usable, is denied on a governed path


@pytest.mark.parametrize("tool_input", [
    {"file_path": GOVERNED},
    {"file_path": GOVERNED, "old_string": OLD},
    {"file_path": GOVERNED, "new_string": NEW},
    {"file_path": GOVERNED, "old_string": None, "new_string": NEW},
    {"file_path": GOVERNED, "old_string": OLD, "new_string": 7},
    {"file_path": GOVERNED, "old_string": ["old"], "new_string": NEW},
])
def test_an_edit_whose_strings_are_not_text_is_denied_even_with_a_receipt(gate, tool_input):
    grant(TARGET, OLD, NEW)
    assert gate(("Edit", tool_input)) == 2


@pytest.mark.parametrize("tool_input", [
    {"file_path": GOVERNED},
    {"file_path": GOVERNED, "content": None},
    {"file_path": GOVERNED, "content": 7},
    {"file_path": GOVERNED, "content": ["x"]},
])
def test_a_write_whose_content_is_not_text_is_denied_even_with_a_receipt(gate, tool_input):
    grant(TARGET, "q", "")
    assert gate(("Write", tool_input)) == 2


@pytest.mark.parametrize("tool_input", [
    {"notebook_path": GOVERNED, "new_source": None},
    {"notebook_path": GOVERNED, "new_source": 7},
    {"notebook_path": GOVERNED, "new_source": ["x"]},
])
def test_a_notebook_edit_whose_new_source_is_not_text_is_denied_even_with_a_receipt(gate, tool_input):
    grant(TARGET, "q", "")
    assert gate(("NotebookEdit", tool_input)) == 2


@pytest.mark.parametrize("edits", [
    [],
    None,
    "one",
    {"old_string": "one", "new_string": "uno"},
    ["one"],
    [None],
    [{"old_string": "one"}],
    [{"new_string": "uno"}],
    [{"old_string": "one", "new_string": 3}],
    [{"old_string": None, "new_string": "uno"}],
    [{"old_string": "one", "new_string": "uno"}, 5],
])
def test_a_multi_edit_without_a_usable_list_of_edits_is_denied_even_with_a_receipt(gate, edits):
    grant(TARGET, "one", "uno")
    assert gate(("MultiEdit", {"file_path": GOVERNED, "edits": edits})) == 2


def test_a_multi_edit_without_the_edits_field_is_denied(gate):
    grant(TARGET, "one", "uno")
    assert gate(("MultiEdit", {"file_path": GOVERNED})) == 2


# T3: the denial says what is missing


def denial(gate, capsys, call):
    assert gate(call) == 2
    return capsys.readouterr().err


def test_a_denial_with_no_receipt_for_the_file_names_what_is_missing_and_does_not_blame_the_content(gate, capsys):
    grant("src/b.py", OLD, NEW)
    err = denial(gate, capsys, edit())
    for needle in (GOVERNED, 'governed_paths entry "src/**"', "source: .actuarii.json", "window: 60 s",
                   "no recent EXECUTE_SAFE receipt for this exact change",
                   f"mcp__boundary-validator__validate_proposal with target_file={GOVERNED}"):
        assert needle in err, needle
    assert "other content" not in err


@pytest.mark.parametrize("call", [
    pytest.param(edit("other", NEW), id="edit-old"),
    pytest.param(edit(OLD, "other"), id="edit-new"),
    pytest.param(write("other"), id="write"),
    pytest.param(notebook("other"), id="notebook"),
    pytest.param(multi_edit((OLD, NEW), ("x", "y")), id="multi-edit"),
])
def test_a_denial_with_receipts_for_other_content_says_so_and_explains_the_correspondence(gate, capsys, call):
    grant(TARGET, OLD, NEW)
    err = denial(gate, capsys, call)
    for needle in (GOVERNED, "src/**", "source: .actuarii.json", "window: 60 s",
                   "no recent EXECUTE_SAFE receipt for this exact change",
                   "recent receipts for this file, but for other content",
                   "old_string", "new_string", "content", "new_source",
                   "Topological_Grounding", "Implementation_Block", "byte for byte",
                   f"mcp__boundary-validator__validate_proposal with target_file={GOVERNED}"):
        assert needle in err, needle


def test_an_expired_receipt_is_not_reported_as_a_receipt_for_other_content(isolate_audit_db, gate, capsys):
    grant(TARGET, OLD, NEW)
    age(isolate_audit_db, 120)
    assert "other content" not in denial(gate, capsys, edit("other", NEW))


@pytest.mark.parametrize("call, field", [
    pytest.param(("Edit", {"file_path": GOVERNED, "old_string": OLD}), "new_string", id="edit"),
    pytest.param(("Write", {"file_path": GOVERNED}), "content", id="write"),
    pytest.param(("NotebookEdit", {"notebook_path": GOVERNED, "new_source": 3}), "new_source", id="notebook"),
    pytest.param(("MultiEdit", {"file_path": GOVERNED, "edits": []}), "edits", id="multi-edit"),
])
def test_a_denial_for_content_that_is_not_text_names_the_tool_and_the_field(gate, capsys, call, field):
    err = denial(gate, capsys, call)
    assert f"tool_input.{field}" in err
    assert call[0] in err


@pytest.mark.parametrize("call", [
    edit("other", NEW), write("other"), notebook("other"), multi_edit(("x", "y")),
])
def test_no_denial_cites_agents_clauses(gate, capsys, call):
    grant(TARGET, OLD, NEW)
    assert "AGENTS" not in denial(gate, capsys, call)


# the queries of the gate


def test_has_receipt_reads_the_exact_pair_by_identity_and_within_the_window(isolate_audit_db):
    grant(TARGET, OLD, NEW)
    path = str(REPO_ROOT / "src" / "a.py")
    assert hook_gate.has_receipt(path, sha(NEW), sha(OLD)) is True
    assert hook_gate.has_receipt(path, sha(NEW)) is True
    assert hook_gate.has_receipt(path, sha(OLD), sha(NEW)) is False
    assert hook_gate.has_receipt(path, sha(NEW), sha("other")) is False
    assert hook_gate.has_receipt(str(REPO_ROOT / "src" / "b.py"), sha(NEW), sha(OLD)) is False
    age(isolate_audit_db, 3600)
    assert hook_gate.has_receipt(path, sha(NEW), sha(OLD), window_seconds=900) is False
    assert hook_gate.has_receipt(path, sha(NEW), sha(OLD), window_seconds=7200) is True


def test_has_any_receipt_ignores_the_content(isolate_audit_db):
    grant(TARGET, OLD, NEW)
    assert hook_gate.has_any_receipt(GOVERNED) is True
    assert hook_gate.has_any_receipt(str(REPO_ROOT / "src" / "b.py")) is False
    age(isolate_audit_db, 3600)
    assert hook_gate.has_any_receipt(GOVERNED, window_seconds=900) is False


@pytest.mark.parametrize("query", [
    lambda: hook_gate.has_receipt(GOVERNED, sha(NEW), sha(OLD)),
    lambda: hook_gate.has_any_receipt(GOVERNED),
], ids=["has_receipt", "has_any_receipt"])
def test_the_queries_raise_when_the_database_or_the_table_is_missing(tmp_path, monkeypatch, query):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path / "absent.db")
    with pytest.raises(sqlite3.Error):
        query()
    present = tmp_path / "present.db"
    with closing(sqlite3.connect(present)) as conn, conn:
        conn.execute("CREATE TABLE audit_log (case_id TEXT)")
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", present)
    with pytest.raises(sqlite3.Error):
        query()


def test_the_gate_fails_closed_when_the_receipt_table_is_missing(gate):
    validator._persist_audit("case-1", "EXECUTE_SAFE", "DOC", TARGET, "NONE")
    assert gate(edit()) == 2


# T4: class 3 keeps the receipt per file


def test_a_class_3_tool_still_needs_a_receipt_for_the_file_and_any_content_will_do(gate):
    tool_input = {"path": GOVERNED}
    assert gate((UNKNOWN, tool_input)) == 2
    grant(TARGET, "whatever", "unrelated")
    assert gate((UNKNOWN, tool_input)) == 0


def test_a_class_3_denial_is_the_per_file_one(gate, capsys):
    grant("docs/decoy.md", "q", "b")
    err = denial(gate, capsys, (UNKNOWN, {"path": GOVERNED}))
    assert "no recent EXECUTE_SAFE in audit_log" in err
    assert "does not know" in err
