"""The write gate records what each allowed write leaves, and denies a write whose record it cannot make (ADR-016).

Before the hook lets an Edit, MultiEdit or Write through on a governed path, it adds one row to the `writes` table of
the audit database: the path as the gate spells it, the tool, the SHA-256 of the file before (NULL when it does not
exist), the SHA-256 of the exact result and the case_ids of the receipts that cover the write. tools/git/commit_record.py
compares those rows with a commit. The tests run in process, as test_content_receipt.py does: the real validator for the
receipts, the real hook on a replaced stdin and the audit database the conftest isolates. A governed file that has to
exist lives under tmp_path, with the REPO_ROOT of the hook, of the gate and of the validator pointed there.
"""
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from contextlib import closing

import pytest

from tools.boundary_validator import hook_gate, validator
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
PREFIX = "[require_boundary_validation] "
RULE = 'governed_paths entry "src/**"'
WRITES_COLUMNS = ["id", "timestamp", "target_file", "tool", "before_sha256", "after_sha256", "receipts"]
UNKNOWN = "mcp__fs__write_file"


def sha(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def proposal(target, grounding, block, rationale):
    return json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target,
        "Topological_Grounding": grounding,
        "Implementation_Block": block,
        "Safety_Abort": "NONE",
        "Rationale": rationale,
    })


def grant(target, grounding, block, rationale="A test proposal."):
    decision = validate_proposal(proposal(target, grounding, block, rationale), target)
    assert decision["final_decision"] == "EXECUTE_SAFE", decision
    return decision["case_id"]


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def writes(db):
    """The rows of the `writes` table in order, as (target_file, tool, before, after, case_ids); [] without the table."""
    with closing(sqlite3.connect(db)) as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'writes'").fetchone() is None:
            return []
        rows = conn.execute(
            "SELECT target_file, tool, before_sha256, after_sha256, receipts FROM writes ORDER BY id").fetchall()
    return [(target, tool, before, after, json.loads(receipts)) for target, tool, before, after, receipts in rows]


def set_receipt_age(db, case_id, seconds):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE receipts SET timestamp = datetime('now', ?) WHERE case_id = ?", (f"-{seconds} seconds", case_id))


def forge_receipt(db, target, grounding, block, case="forged"):
    """A receipt the validator would not issue for this change, written straight into the table."""
    with closing(sqlite3.connect(db)) as conn, conn:
        validator._insert_receipt(conn, case, target, sha(grounding), sha(block))


def edit(path, old, new, **extra):
    return "Edit", {"file_path": str(path), "old_string": old, "new_string": new, **extra}


def multi_edit(path, *pairs):
    return "MultiEdit", {"file_path": str(path),
                         "edits": [{"old_string": old, "new_string": new} for old, new in pairs]}


def write(path, content):
    return "Write", {"file_path": str(path), "content": content}


def notebook(path, new_source):
    return "NotebookEdit", {"notebook_path": str(path), "new_source": new_source}


@pytest.fixture
def repo(tmp_path, monkeypatch, config_file):
    """A repository root under tmp_path that governs src/**, for the hook, the gate and the validator."""
    config_file(CONFIG)
    root = (tmp_path / "repo").resolve()
    (root / "src").mkdir(parents=True)
    for module in (require_boundary_validation, hook_gate, validator):
        monkeypatch.setattr(module, "REPO_ROOT", root)
    return root


@pytest.fixture
def gate(repo, monkeypatch):
    def run(call):
        tool, tool_input = call
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": tool, "tool_input": tool_input})))
        return require_boundary_validation.main()

    return run


def prepare(repo, tool):
    """src/a.txt holds `one two`, the receipts for a call of `tool` on it exist; returns the call."""
    path = repo / "src" / "a.txt"
    put(path, "one two\n")
    if tool == "Write":
        grant("src/a.txt", "one", "uno dos\n")
        return write(path, "uno dos\n")
    if tool == "Edit":
        grant("src/a.txt", "one", "uno")
        return edit(path, "one", "uno")
    grant("src/a.txt", "one", "uno")
    grant("src/a.txt", "two", "dos")
    return multi_edit(path, ("one", "uno"), ("two", "dos"))


# T1: an allowed Edit, MultiEdit or Write leaves one row with the exact result


def test_a_write_of_a_new_file_leaves_a_row_with_no_before_and_the_hash_of_the_content(repo, gate, isolate_audit_db):
    case = grant("src/new.txt", "", "hello\n")
    assert gate(write(repo / "src" / "new.txt", "hello\n")) == 0
    assert writes(isolate_audit_db) == [("src/new.txt", "Write", None, sha("hello\n"), [case])]


def test_a_write_over_a_file_leaves_the_hash_of_the_bytes_it_has_as_the_before(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "old\n")
    case = grant("src/a.txt", "old", "new\n")
    assert gate(write(repo / "src" / "a.txt", "new\n")) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "Write", sha("old\n"), sha("new\n"), [case])]


def test_a_write_over_a_file_that_is_not_utf8_leaves_the_hash_of_its_bytes_as_the_before(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.bin", b"data \xff\xfe")
    case = grant("src/a.bin", "data", "text\n")
    assert gate(write(repo / "src" / "a.bin", "text\n")) == 0
    assert writes(isolate_audit_db) == [("src/a.bin", "Write", sha(b"data \xff\xfe"), sha("text\n"), [case])]


@pytest.mark.parametrize("extra, left", [({}, "1 two one\n"), ({"replace_all": True}, "1 two 1\n")],
                         ids=["first-occurrence", "replace-all"])
def test_an_edit_leaves_the_hash_of_the_file_with_the_edit_applied_as_the_tool_applies_it(
        repo, gate, isolate_audit_db, extra, left):
    put(repo / "src" / "a.txt", "one two one\n")
    case = grant("src/a.txt", "one", "1")
    assert gate(edit(repo / "src" / "a.txt", "one", "1", **extra)) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "Edit", sha("one two one\n"), sha(left), [case])]


def test_an_edit_with_an_empty_old_string_leaves_the_new_string_as_the_content(repo, gate, isolate_audit_db):
    case = grant("src/new.txt", "", "created\n")
    assert gate(edit(repo / "src" / "new.txt", "", "created\n")) == 0
    assert writes(isolate_audit_db) == [("src/new.txt", "Edit", None, sha("created\n"), [case])]


def test_a_multi_edit_leaves_the_result_of_its_edits_applied_in_order_and_the_case_of_each_receipt(
        repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "a b\n")
    first = grant("src/a.txt", "a", "b")
    second = grant("src/a.txt", "b", "c")
    assert gate(multi_edit(repo / "src" / "a.txt", ("a", "b"), ("b", "c"))) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "MultiEdit", sha("a b\n"), sha("c b\n"), [first, second])]


def test_a_receipt_that_covers_two_edits_is_listed_once_for_each(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "x x\n")
    case = grant("src/a.txt", "x", "y")
    assert gate(multi_edit(repo / "src" / "a.txt", ("x", "y"), ("x", "y"))) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "MultiEdit", sha("x x\n"), sha("y y\n"), [case, case])]


def test_the_row_names_the_most_recent_receipt_by_time_and_then_by_order(repo, gate, isolate_audit_db):
    older = grant("src/new.txt", "", "x\n")
    newer = grant("src/new.txt", "", "x\n")
    call = write(repo / "src" / "new.txt", "x\n")
    assert gate(call) == 0
    assert writes(isolate_audit_db)[-1][4] == [newer]
    set_receipt_age(isolate_audit_db, older, 5)
    set_receipt_age(isolate_audit_db, newer, 30)
    assert gate(call) == 0
    assert writes(isolate_audit_db)[-1][4] == [older]


def test_a_path_spelled_through_dot_dot_is_stored_as_the_repository_relative_path_the_gate_resolves(
        repo, gate, isolate_audit_db):
    case = grant("src/a.txt", "", "x\n")
    assert gate(write(repo / "src" / ".." / "src" / "a.txt", "x\n")) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "Write", None, sha("x\n"), [case])]


@pytest.mark.parametrize("content", ["a\r\nb\r\n", "tab\there  \n", "é ☃ \U0001f600\n", "no newline", ""],
                         ids=["crlf", "whitespace", "non-ascii", "no-final-newline", "empty"])
def test_the_after_is_the_hash_of_the_exact_utf8_bytes_of_the_result_with_nothing_normalised(
        repo, gate, isolate_audit_db, content):
    case = grant("src/new.txt", "", content)
    assert gate(write(repo / "src" / "new.txt", content)) == 0
    assert writes(isolate_audit_db) == [("src/new.txt", "Write", None, sha(content.encode("utf-8")), [case])]


def test_an_edit_of_a_file_with_crlf_line_endings_keeps_them(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "one\r\ntwo\r\n")
    case = grant("src/a.txt", "two", "2")
    assert gate(edit(repo / "src" / "a.txt", "two", "2")) == 0
    assert writes(isolate_audit_db) == [("src/a.txt", "Edit", sha("one\r\ntwo\r\n"), sha("one\r\n2\r\n"), [case])]


def test_every_allowed_write_leaves_its_own_row_in_order(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "one\n")
    first = grant("src/a.txt", "one", "two")
    assert gate(edit(repo / "src" / "a.txt", "one", "two")) == 0
    put(repo / "src" / "a.txt", "two\n")
    second = grant("src/a.txt", "two", "three")
    assert gate(edit(repo / "src" / "a.txt", "two", "three")) == 0
    assert writes(isolate_audit_db) == [
        ("src/a.txt", "Edit", sha("one\n"), sha("two\n"), [first]),
        ("src/a.txt", "Edit", sha("two\n"), sha("three\n"), [second]),
    ]


def test_a_governed_python_file_is_recorded_once_its_primitive_check_has_passed(repo, gate, isolate_audit_db):
    case = grant("src/a.py", "", "x = 1\n")
    assert gate(write(repo / "src" / "a.py", "x = 1\n")) == 0
    assert writes(isolate_audit_db) == [("src/a.py", "Write", None, sha("x = 1\n"), [case])]


def test_the_row_carries_a_timestamp(repo, gate, isolate_audit_db):
    grant("src/new.txt", "", "x\n")
    assert gate(write(repo / "src" / "new.txt", "x\n")) == 0
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        [(stamp,)] = conn.execute("SELECT timestamp FROM writes").fetchall()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", stamp)


# T2: a write whose row cannot be written is denied, with the target, the rule, its source and the error


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
def test_a_write_is_denied_when_the_writes_table_has_another_shape_and_the_denial_says_what_and_why(
        repo, gate, isolate_audit_db, capsys, tool):
    call = prepare(repo, tool)
    with closing(sqlite3.connect(isolate_audit_db)) as conn, conn:
        conn.execute("CREATE TABLE writes (unrelated TEXT)")
    assert gate(call) == 2
    err = capsys.readouterr().err
    assert err.startswith(PREFIX) and len(err.splitlines()) == 1, err
    for needle in (str(repo / "src" / "a.txt"), RULE, "source: .actuarii.json",
                   "could not record in the audit trail", "OperationalError", "writes"):
        assert needle in err, needle
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert [column[1] for column in conn.execute("PRAGMA table_info(writes)")] == ["unrelated"]
        assert conn.execute("SELECT COUNT(*) FROM writes").fetchone() == (0,)


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes a file whatever its mode")
def test_a_write_is_denied_when_the_audit_database_can_be_read_but_not_written(repo, gate, isolate_audit_db, capsys):
    call = prepare(repo, "Write")
    os.chmod(isolate_audit_db, 0o444)
    assert gate(call) == 2
    err = capsys.readouterr().err
    assert err.startswith(PREFIX) and len(err.splitlines()) == 1, err
    for needle in (str(repo / "src" / "a.txt"), RULE, "source: .actuarii.json", "could not record in the audit trail"):
        assert needle in err, needle
    assert writes(isolate_audit_db) == []


def test_a_write_to_a_path_the_gate_cannot_read_is_denied_and_records_nothing(repo, gate, isolate_audit_db, capsys):
    grant("src/a.txt", "", "x\n")
    (repo / "src" / "a.txt").mkdir()
    assert gate(write(repo / "src" / "a.txt", "x\n")) == 2
    err = capsys.readouterr().err
    assert err.startswith(PREFIX) and len(err.splitlines()) == 1, err
    for needle in (str(repo / "src" / "a.txt"), RULE, "source: .actuarii.json", "cannot read"):
        assert needle in err, needle
    assert writes(isolate_audit_db) == []


# T3: the queries and the writer of hook_gate


def test_receipt_case_is_the_most_recent_matching_receipt_by_time_and_then_by_order(repo, isolate_audit_db):
    path = str(repo / "src" / "a.txt")
    first = grant("src/a.txt", "q", "b")
    second = grant("src/a.txt", "q", "b")
    other = grant("src/a.txt", "q", "other")
    assert hook_gate.receipt_case(path, sha("b"), sha("q")) == second
    assert hook_gate.receipt_case(path, sha("other"), sha("q")) == other
    set_receipt_age(isolate_audit_db, first, 5)
    set_receipt_age(isolate_audit_db, second, 30)
    assert hook_gate.receipt_case(path, sha("b"), sha("q")) == first


def test_receipt_case_takes_any_citation_when_none_is_given_and_the_exact_one_otherwise(repo):
    path = str(repo / "src" / "a.txt")
    case = grant("src/a.txt", "q", "b")
    assert hook_gate.receipt_case(path, sha("b")) == case
    assert hook_gate.receipt_case(path, sha("b"), sha("q")) == case
    assert hook_gate.receipt_case(path, sha("b"), sha("other")) is None
    assert hook_gate.receipt_case(path, sha("other")) is None


def test_receipt_case_is_none_for_another_file_and_matches_a_file_by_identity(repo):
    case = grant("src/a.txt", "q", "b")
    assert hook_gate.receipt_case(str(repo / "src" / "b.txt"), sha("b"), sha("q")) is None
    assert hook_gate.receipt_case(str(repo / "src" / ".." / "src" / "a.txt"), sha("b"), sha("q")) == case


def test_receipt_case_counts_only_the_receipts_within_the_window(repo, isolate_audit_db):
    path = str(repo / "src" / "a.txt")
    case = grant("src/a.txt", "q", "b")
    set_receipt_age(isolate_audit_db, case, 3600)
    assert hook_gate.receipt_case(path, sha("b"), sha("q"), window_seconds=900) is None
    assert hook_gate.receipt_case(path, sha("b"), sha("q"), window_seconds=7200) == case
    assert hook_gate.receipt_case(path, sha("b"), sha("q")) is None


def test_receipt_case_raises_when_the_database_or_the_table_is_missing(repo, tmp_path, monkeypatch):
    path = str(repo / "src" / "a.txt")
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path / "absent.db")
    with pytest.raises(sqlite3.Error):
        hook_gate.receipt_case(path, sha("b"))
    present = tmp_path / "present.db"
    with closing(sqlite3.connect(present)) as conn, conn:
        conn.execute("CREATE TABLE audit_log (case_id TEXT)")
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", present)
    with pytest.raises(sqlite3.Error):
        hook_gate.receipt_case(path, sha("b"))


def test_record_write_adds_the_row_and_creates_the_table_in_a_database_that_has_none(repo, isolate_audit_db):
    grant("src/a.txt", "", "x\n")
    hook_gate.record_write("src/a.txt", "Write", None, sha("x\n"), ["c1", "c2"])
    hook_gate.record_write("src/a.txt", "Edit", sha("x\n"), sha("y\n"), [])
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert [column[1] for column in conn.execute("PRAGMA table_info(writes)")] == WRITES_COLUMNS
        rows = conn.execute("SELECT target_file, tool, before_sha256, after_sha256, receipts FROM writes ORDER BY id")
        assert rows.fetchall() == [
            ("src/a.txt", "Write", None, sha("x\n"), '["c1", "c2"]'),
            ("src/a.txt", "Edit", sha("x\n"), sha("y\n"), "[]"),
        ]
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone() == (1,)


def test_record_write_numbers_the_rows_in_the_order_they_are_recorded(repo, isolate_audit_db):
    grant("src/a.txt", "", "x\n")
    for index in range(3):
        hook_gate.record_write("src/a.txt", "Write", None, sha(str(index)), [])
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert conn.execute("SELECT id, after_sha256 FROM writes ORDER BY id").fetchall() == [
            (1, sha("0")), (2, sha("1")), (3, sha("2"))]


def test_record_write_never_creates_a_missing_database_nor_its_directory(tmp_path, monkeypatch):
    missing = tmp_path / "no-such-directory" / "audit.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", missing)
    with pytest.raises(sqlite3.Error):
        hook_gate.record_write("src/a.txt", "Write", None, sha("x"), [])
    assert not missing.parent.exists()
    inside = tmp_path / "audit.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", inside)
    with pytest.raises(sqlite3.Error):
        hook_gate.record_write("src/a.txt", "Write", None, sha("x"), [])
    assert not inside.exists()


def test_record_write_makes_the_table_and_the_row_in_one_transaction(repo, isolate_audit_db):
    grant("src/a.txt", "", "x\n")
    with pytest.raises(sqlite3.IntegrityError):
        hook_gate.record_write("src/a.txt", "Write", None, None, [])
    with closing(sqlite3.connect(isolate_audit_db)) as conn:
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'writes'").fetchone() is None


def test_recorded_writes_gives_the_rows_of_one_file_in_order_with_the_rationales_of_their_receipts(repo):
    first = grant("src/a.txt", "", "one\n", "The first reason.")
    second = grant("src/a.txt", "", "two\n", "The second reason.")
    hook_gate.record_write("src/a.txt", "Write", None, "h1", [first])
    hook_gate.record_write("src/b.txt", "Write", None, "hb", [second])
    hook_gate.record_write("src/a.txt", "MultiEdit", "h1", "h2", [second, first])
    hook_gate.record_write("src/a.txt", "Edit", "h2", "h3", [second, second])
    assert hook_gate.recorded_writes("src/a.txt") == [
        (None, "h1", ["The first reason."]),
        ("h1", "h2", ["The second reason.", "The first reason."]),
        ("h2", "h3", ["The second reason."]),
    ]
    assert hook_gate.recorded_writes("src/b.txt") == [(None, "hb", ["The second reason."])]
    assert hook_gate.recorded_writes("src/c.txt") == []


def test_recorded_writes_keeps_the_order_of_the_rows_whatever_their_timestamps(repo, isolate_audit_db):
    case = grant("src/a.txt", "", "one\n")
    for index in range(3):
        hook_gate.record_write("src/a.txt", "Write", None, f"h{index}", [case])
    with closing(sqlite3.connect(isolate_audit_db)) as conn, conn:
        conn.execute("UPDATE writes SET timestamp = datetime('now', '-' || id || ' hours')")
    assert [after for _before, after, _rationales in hook_gate.recorded_writes("src/a.txt")] == ["h0", "h1", "h2"]


def test_a_receipt_that_audit_log_does_not_have_or_whose_rationale_is_null_gives_none(repo):
    known = grant("src/a.txt", "", "one\n", "A reason.")
    validator._persist_audit("without-rationale", "EXECUTE_SAFE", "DOC", "src/a.txt", "NONE", None)
    hook_gate.record_write("src/a.txt", "Edit", None, "h1", ["without-rationale", known, "no-such-case"])
    assert hook_gate.recorded_writes("src/a.txt") == [(None, "h1", [None, "A reason.", None])]


def test_recorded_writes_matches_the_file_as_the_gate_stored_it_and_not_by_identity(repo):
    case = grant("src/a.txt", "", "one\n")
    hook_gate.record_write("src/a.txt", "Write", None, "h1", [case])
    assert hook_gate.recorded_writes("src/../src/a.txt") == []
    assert hook_gate.recorded_writes("SRC/a.txt") == []


def test_recorded_writes_of_a_database_without_the_writes_table_is_empty(repo):
    grant("src/a.txt", "", "one\n")
    assert hook_gate.recorded_writes("src/a.txt") == []


def test_recorded_writes_raises_when_the_database_is_missing_or_has_no_audit_log(tmp_path, monkeypatch):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path / "absent.db")
    with pytest.raises(sqlite3.Error):
        hook_gate.recorded_writes("src/a.txt")
    present = tmp_path / "present.db"
    with closing(sqlite3.connect(present)) as conn, conn:
        conn.execute("CREATE TABLE receipts (case_id TEXT)")
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", present)
    hook_gate.record_write("src/a.txt", "Write", None, "h1", ["c1"])
    with pytest.raises(sqlite3.Error):
        hook_gate.recorded_writes("src/a.txt")


def test_recorded_writes_does_not_write(repo, isolate_audit_db):
    case = grant("src/a.txt", "", "one\n")
    hook_gate.record_write("src/a.txt", "Write", None, "h1", [case])
    os.chmod(isolate_audit_db, 0o444)
    assert hook_gate.recorded_writes("src/a.txt") == [(None, "h1", ["A test proposal."])]


# T4: what the gate decided before, and what it records nothing for, stays as it was


def test_a_notebook_edit_with_its_receipt_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    grant("src/nb.ipynb", "", "print(1)")
    assert gate(notebook(repo / "src" / "nb.ipynb", "print(1)")) == 0
    assert writes(isolate_audit_db) == []


def test_a_tool_the_gate_does_not_know_is_allowed_with_a_receipt_for_the_file_and_records_nothing(
        repo, gate, isolate_audit_db):
    grant("src/a.txt", "", "anything")
    assert gate((UNKNOWN, {"path": str(repo / "src" / "a.txt")})) == 0
    assert writes(isolate_audit_db) == []


def test_an_edit_of_a_file_that_is_not_utf8_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.bin", b"old \xff\xfe")
    grant("src/a.bin", "old", "new")
    assert gate(edit(repo / "src" / "a.bin", "old", "new")) == 0
    assert writes(isolate_audit_db) == []


def test_an_edit_with_an_empty_old_string_of_a_file_that_is_not_utf8_records_nothing(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.bin", b"data \xff\xfe")
    forge_receipt(isolate_audit_db, "src/a.bin", "", "new")
    assert gate(edit(repo / "src" / "a.bin", "", "new")) == 0
    assert writes(isolate_audit_db) == []


def test_an_edit_whose_old_string_is_not_in_the_file_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "present\n")
    grant("src/a.txt", "present", "other")
    put(repo / "src" / "a.txt", "changed meanwhile\n")
    assert gate(edit(repo / "src" / "a.txt", "present", "other")) == 0
    assert writes(isolate_audit_db) == []


def test_an_edit_of_a_file_that_does_not_exist_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    grant("src/missing.txt", "x", "y")
    assert gate(edit(repo / "src" / "missing.txt", "x", "y")) == 0
    assert writes(isolate_audit_db) == []


def test_a_multi_edit_with_an_edit_that_cannot_apply_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.txt", "one\n")
    grant("src/a.txt", "one", "uno")
    put(repo / "src" / "a.txt", "one two\n")
    grant("src/a.txt", "two", "dos")
    put(repo / "src" / "a.txt", "one\n")
    assert gate(multi_edit(repo / "src" / "a.txt", ("one", "uno"), ("two", "dos"))) == 0
    assert writes(isolate_audit_db) == []


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
def test_a_write_without_its_receipt_is_denied_and_records_nothing(repo, gate, isolate_audit_db, tool):
    call = prepare(repo, tool)
    tool_input = dict(call[1])
    if tool == "Write":
        tool_input["content"] = "other\n"
    elif tool == "Edit":
        tool_input["new_string"] = "other"
    else:
        tool_input["edits"] = [{"old_string": "one", "new_string": "other"}]
    assert gate((tool, tool_input)) == 2
    assert writes(isolate_audit_db) == []


def test_a_path_that_no_rule_governs_is_allowed_and_records_nothing(repo, gate, isolate_audit_db):
    grant("src/a.txt", "", "x")
    assert gate(write(repo / "docs" / "x.md", "# Title\n")) == 0
    assert writes(isolate_audit_db) == []


def test_a_governed_python_file_that_is_not_utf8_is_still_denied_and_records_nothing(repo, gate, isolate_audit_db):
    put(repo / "src" / "a.py", b"x = 1  # \xff\n")
    forge_receipt(isolate_audit_db, "src/a.py", "x = 1", "x = 2")
    assert gate(edit(repo / "src" / "a.py", "x = 1", "x = 2")) == 2
    assert writes(isolate_audit_db) == []


def test_a_python_write_that_introduces_a_primitive_is_still_denied_and_records_nothing(repo, gate, isolate_audit_db):
    text = "import subprocess\n"
    forge_receipt(isolate_audit_db, "src/new.py", "", text)
    assert gate(write(repo / "src" / "new.py", text)) == 2
    assert writes(isolate_audit_db) == []


def test_a_write_with_no_audit_trail_is_denied_and_creates_neither_a_database_nor_a_directory(
        repo, gate, tmp_path, monkeypatch):
    missing = tmp_path / "no-trail" / "audit.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", missing)
    assert gate(write(repo / "src" / "a.txt", "x\n")) == 2
    assert not missing.parent.exists()
