"""Every proposal carries its Rationale, and no EXECUTE_SAFE exists without its record.

The audit trail is meant to say what an agent did and why. A proposal has a required `Rationale` (1 to 1000
characters, not only whitespace) that the validator records, byte for byte, with every decision it takes on a
proposal that passed the schema. An EXECUTE_SAFE exists only with its audit row and its receipt, written in one
SQLite transaction; when that fails the decision is ABORTED_NOT_RECORDED and nothing remains. An audit database
created before the column existed is migrated in place. The tests run the validator in process over the audit
database the conftest isolates; the hook is the real one on a replaced stdin.
"""
import hashlib
import io
import json
import re
import sqlite3
import sys
import uuid
from contextlib import closing

import pytest

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.hook_gate import REPO_ROOT
from tools.boundary_validator.schemas.proposals import AgentMutationProposal, build_response_format
from tools.boundary_validator.validator import TOOL_DEFINITION, handle_request, validate_proposal
from tools.hooks import require_boundary_validation

LF = chr(10)
CR = chr(13)
TAB = chr(9)
QUOTE = chr(34)
BACKSLASH = chr(92)
NUL = chr(0)
SURROGATE = chr(0xD800)

TARGET = "docs/x.md"
RATIONALE = "The record names the fields of a proposal but not the reason, so a reader cannot tell why it was made."
NOT_RECORDED = "the audit trail could not be written, so no receipt was issued"
EXACT = (" Why: 'single' and " + QUOTE + "double" + QUOTE + ", caf" + chr(0xE9) + " " + chr(0x2603) + " " + chr(0x1F600)
         + CR + LF + "second line" + TAB + "back" + BACKSLASH + "slash " + LF)

CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 60,
}
GOVERNED_TARGET = "src/a.txt"
GOVERNED = str(REPO_ROOT / "src" / "a.txt")
OLD = "old text" + LF
NEW = "new text" + LF

BASE_TABLES = """
CREATE TABLE audit_log (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    intent_class TEXT,
    target_file TEXT,
    decision TEXT NOT NULL,
    safety_abort TEXT
);
CREATE TABLE receipts (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    target_file TEXT NOT NULL,
    grounding_sha256 TEXT NOT NULL,
    block_sha256 TEXT NOT NULL
);
"""


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


OLD_AUDIT = [
    ("old-1", "2020-01-01 10:00:00", "DOC", "docs/old.md", "EXECUTE_SAFE", "NONE"),
    ("old-2", "2020-01-01 10:05:00", "FIX", "docs/old.md", "ABORTED_GROUNDING_FAILED", "NONE"),
]
OLD_RECEIPTS = [("old-1", "2020-01-01 10:00:00", "docs/old.md", sha("a"), sha("b"))]


def body(rationale=RATIONALE, **fields):
    proposal = {
        "Intent_Class": "DOC",
        "Target_File": TARGET,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
        "Rationale": rationale,
    }
    proposal.update(fields)
    return proposal


def without_rationale():
    proposal = body()
    del proposal["Rationale"]
    return proposal


def submit(proposal, target=None):
    return validate_proposal(json.dumps(proposal), proposal["Target_File"] if target is None else target)


def table_rows(db, table, columns="*", tail=""):
    with closing(sqlite3.connect(db)) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone():
            return []
        return conn.execute(f"SELECT {columns} FROM {table} {tail}").fetchall()


def audit_columns(db):
    with closing(sqlite3.connect(db)) as conn:
        return [row[1] for row in conn.execute("PRAGMA table_info(audit_log)")]


def audit_row(db, case_id):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT decision, rationale FROM audit_log WHERE case_id = ?", (case_id,)).fetchall()


def run_script(db, script):
    with closing(sqlite3.connect(db)) as conn:
        conn.executescript(script)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "a.txt").write_text("alpha beta" + LF, encoding="utf-8")
    return tmp_path


@pytest.fixture
def old_database(isolate_audit_db):
    """An audit database as the base commit created it: no rationale column, rows, and a receipt."""
    run_script(isolate_audit_db, BASE_TABLES)
    with closing(sqlite3.connect(isolate_audit_db)) as conn, conn:
        conn.executemany(
            "INSERT INTO audit_log (case_id, timestamp, intent_class, target_file, decision, safety_abort) "
            "VALUES (?, ?, ?, ?, ?, ?)", OLD_AUDIT)
        conn.executemany(
            "INSERT INTO receipts (case_id, timestamp, target_file, grounding_sha256, block_sha256) "
            "VALUES (?, ?, ?, ?, ?)", OLD_RECEIPTS)
    return isolate_audit_db


@pytest.fixture
def gate(monkeypatch, config_file):
    config_file(CONFIG)

    def run(tool, tool_input):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": tool, "tool_input": tool_input})))
        return require_boundary_validation.main()

    return run


def edit(old, new, file_path=GOVERNED):
    return "Edit", {"file_path": file_path, "old_string": old, "new_string": new}


# T1: the Rationale is required, and it is a string of 1 to 1000 characters that is not only whitespace


def test_a_proposal_with_a_rationale_is_an_execute_safe():
    decision = submit(body())
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert decision["status"] == "VALIDATED"


@pytest.mark.parametrize("rationale", [
    pytest.param("x", id="one-character"),
    pytest.param("x" * 1000, id="1000-characters"),
    pytest.param(" " * 999 + "x", id="999-spaces-and-a-letter"),
    pytest.param(chr(0xE9) * 1000, id="1000-two-byte-characters"),
    pytest.param(chr(0x1F600) * 1000, id="1000-four-byte-characters"),
    pytest.param("first line" + LF + "second line", id="two-lines"),
    pytest.param(" padded ", id="padded"),
])
def test_a_rationale_of_one_to_a_thousand_characters_with_one_that_is_not_whitespace_passes(rationale):
    assert submit(body(rationale))["final_decision"] == "EXECUTE_SAFE"


def test_a_proposal_without_a_rationale_is_a_schema_violation_and_leaves_no_receipt(isolate_audit_db):
    decision = submit(without_rationale())
    assert decision["final_decision"] == "INVALID_JSON"
    assert decision["status"] == "QUARANTINED"
    assert table_rows(isolate_audit_db, "receipts") == []
    assert submit(body())["final_decision"] == "EXECUTE_SAFE"


@pytest.mark.parametrize("rationale", [
    pytest.param("", id="empty"),
    pytest.param(" ", id="space"),
    pytest.param("  " + LF + TAB, id="whitespace"),
    pytest.param(chr(0xA0) + chr(0x2003) + chr(0x3000), id="unicode-whitespace"),
    pytest.param("x" * 1001, id="1001-characters"),
    pytest.param(chr(0xE9) * 1001, id="1001-two-byte-characters"),
    pytest.param(" " * 1001, id="1001-spaces"),
    pytest.param(7, id="number"),
    pytest.param(True, id="boolean"),
    pytest.param(None, id="null"),
    pytest.param(["why"], id="list"),
    pytest.param({"why": "because"}, id="object"),
    pytest.param("lone surrogate " + SURROGATE, id="lone-surrogate"),
])
def test_a_rationale_that_is_not_a_string_of_up_to_a_thousand_characters_with_one_visible_is_a_schema_violation(
        isolate_audit_db, rationale):
    decision = submit(body(rationale))
    assert decision["final_decision"] == "INVALID_JSON"
    assert decision["status"] == "QUARANTINED"
    assert table_rows(isolate_audit_db, "receipts") == []
    assert submit(body())["final_decision"] == "EXECUTE_SAFE"


# T2: every decision taken on a proposal that passed the schema records its Rationale, byte for byte


def test_an_execute_safe_row_holds_the_rationale_byte_for_byte_and_its_receipt_is_in_the_same_database(
        isolate_audit_db):
    decision = submit(body(EXACT))
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert audit_row(isolate_audit_db, decision["case_id"]) == [("EXECUTE_SAFE", EXACT)]
    assert [row[0] for row in table_rows(isolate_audit_db, "receipts", "case_id")] == [decision["case_id"]]


@pytest.mark.parametrize("rationale", ["x" * 1000, chr(0xE9) * 1000, " " * 999 + "x"], ids=["ascii", "two-byte", "spaces"])
def test_a_rationale_of_a_thousand_characters_is_recorded_whole(isolate_audit_db, rationale):
    decision = submit(body(rationale))
    assert audit_row(isolate_audit_db, decision["case_id"]) == [("EXECUTE_SAFE", rationale)]


REFUSALS = [
    pytest.param(body(Target_File="a.txt", Topological_Grounding="alpha", Safety_Abort="BOUNDARY_VIOLATION"),
                 "a.txt", "BLOCKED_BY_SAFETY_GATE", id="safety-abort"),
    pytest.param(body(Target_File="b.txt", Topological_Grounding="alpha"),
                 "a.txt", "ABORTED_TARGET_MISMATCH", id="target-mismatch"),
    pytest.param(body(Intent_Class="FIX", Target_File="a.txt", Topological_Grounding="not in the file"),
                 "a.txt", "ABORTED_GROUNDING_FAILED", id="grounding-failure"),
    pytest.param(body(Target_File="c.py", Topological_Grounding="", Implementation_Block="import subprocess" + LF),
                 "c.py", "ABORTED_VIOLATES_ZERO_TRUST", id="primitive-in-a-python-result"),
    pytest.param(body(Target_File="c.py", Topological_Grounding="", Implementation_Block="def (:" + LF),
                 "c.py", "BLOCKED_BY_SAFETY_GATE", id="python-result-that-does-not-parse"),
    pytest.param(body(Target_File="c.txt", Topological_Grounding=SURROGATE),
                 "c.txt", "ABORTED_GROUNDING_FAILED", id="text-that-cannot-be-hashed"),
]


@pytest.mark.parametrize("proposal, target, expected", REFUSALS)
def test_a_refusal_after_the_schema_records_the_rationale(root, isolate_audit_db, proposal, target, expected):
    decision = submit(proposal, target)
    assert decision["final_decision"] == expected
    assert audit_row(isolate_audit_db, decision["case_id"]) == [(expected, RATIONALE)]


@pytest.mark.parametrize("text, expected", [
    pytest.param("{not json", "INVALID_JSON", id="invalid-json"),
    pytest.param("[1]", "INVALID_JSON", id="not-an-object"),
    pytest.param(json.dumps(body()) + NUL, "ABORTED_VIOLATES_ZERO_TRUST", id="raw-nul"),
    pytest.param(json.dumps(body("bad" + NUL + "reason")), "ABORTED_VIOLATES_ZERO_TRUST", id="nul-in-the-rationale"),
    pytest.param(json.dumps(body("")), "INVALID_JSON", id="empty-rationale"),
    pytest.param(json.dumps(without_rationale()), "INVALID_JSON", id="no-rationale"),
    pytest.param(json.dumps(body(injected="field")), "INVALID_JSON", id="extra-field"),
    pytest.param(json.dumps(body(Safety_Abort="SOMETHING")), "BLOCKED_BY_SAFETY_GATE", id="unknown-safety-abort"),
])
def test_a_decision_taken_before_the_schema_passes_records_no_rationale(isolate_audit_db, text, expected):
    assert validate_proposal(text, TARGET)["final_decision"] == expected
    assert table_rows(isolate_audit_db, "audit_log", "decision, rationale") == [(expected, None)]


def test_persist_audit_takes_the_rationale_as_a_sixth_parameter_that_defaults_to_none(isolate_audit_db):
    validator._persist_audit("case-5", "EXECUTE_SAFE", "DOC", TARGET, "NONE")
    validator._persist_audit("case-6", "EXECUTE_SAFE", "DOC", TARGET, "NONE", "because")
    assert table_rows(isolate_audit_db, "audit_log", "case_id, rationale", "ORDER BY case_id") == [
        ("case-5", None), ("case-6", "because")]


def test_a_tools_call_over_the_server_carries_the_rationale_into_the_record(isolate_audit_db):
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "validate_proposal", "arguments": {"proposal": body(), "target_file": TARGET}}})
    decision = json.loads(response["result"]["content"][0]["text"])
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert audit_row(isolate_audit_db, decision["case_id"]) == [("EXECUTE_SAFE", RATIONALE)]
    response = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "validate_proposal", "arguments": {"proposal": without_rationale(), "target_file": TARGET}}})
    assert json.loads(response["result"]["content"][0]["text"])["final_decision"] == "INVALID_JSON"


# T3: the strict response format and the published input schema require the Rationale


def test_the_strict_response_format_requires_the_rationale_as_a_described_string():
    schema = build_response_format(AgentMutationProposal)["json_schema"]["schema"]
    assert "Rationale" in schema["required"]
    assert schema["properties"]["Rationale"]["type"] == "string"
    assert "why" in schema["properties"]["Rationale"]["description"].lower()


def test_the_input_schema_that_tools_list_returns_requires_the_rationale_in_the_proposal():
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    proposal = response["result"]["tools"][0]["inputSchema"]["properties"]["proposal"]
    assert "Rationale" in proposal["required"]
    assert proposal["properties"]["Rationale"]["type"] == "string"
    assert proposal["additionalProperties"] is False


# T4: an audit database created before the column existed is migrated in place


def test_an_old_database_is_migrated_by_the_next_validation_and_keeps_its_rows(old_database):
    decision = submit(body())
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert audit_columns(old_database).count("rationale") == 1
    audit = {row[0]: row for row in table_rows(
        old_database, "audit_log",
        "case_id, timestamp, intent_class, target_file, decision, safety_abort, rationale")}
    assert [audit[case_id] for case_id in ("old-1", "old-2")] == [row + (None,) for row in OLD_AUDIT]
    assert audit[decision["case_id"]][4:] == ("EXECUTE_SAFE", "NONE", RATIONALE)
    receipts = {row[0] for row in table_rows(old_database, "receipts", "case_id")}
    assert receipts == {"old-1", decision["case_id"]}
    assert table_rows(old_database, "receipts", "case_id, timestamp, target_file, grounding_sha256, block_sha256",
                      "WHERE case_id = 'old-1'") == OLD_RECEIPTS


def test_a_refusal_as_the_first_write_also_migrates_an_old_database(old_database):
    decision = submit(body(Safety_Abort="BOUNDARY_VIOLATION"))
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"
    assert audit_row(old_database, decision["case_id"]) == [("BLOCKED_BY_SAFETY_GATE", RATIONALE)]
    assert audit_row(old_database, "old-1") == [("EXECUTE_SAFE", None)]
    assert audit_row(old_database, "old-2") == [("ABORTED_GROUNDING_FAILED", None)]


def test_a_second_validation_leaves_the_migrated_database_as_it_is(old_database):
    first = submit(body())
    second = submit(body("another reason"))
    assert (first["final_decision"], second["final_decision"]) == ("EXECUTE_SAFE", "EXECUTE_SAFE")
    assert audit_columns(old_database).count("rationale") == 1
    assert audit_row(old_database, second["case_id"]) == [("EXECUTE_SAFE", "another reason")]


def test_a_migrated_database_still_serves_its_receipt_to_the_hook(old_database, gate):
    assert gate(*edit(OLD, NEW)) == 2
    decision = submit(body(Target_File=GOVERNED_TARGET, Topological_Grounding=OLD, Implementation_Block=NEW))
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert gate(*edit(OLD, NEW)) == 0
    assert gate(*edit(OLD, "other")) == 2


# T5: no EXECUTE_SAFE when its record cannot be written


def test_an_execute_safe_is_not_issued_when_the_audit_database_cannot_be_written(tmp_path, monkeypatch):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path)
    decision = submit(body())
    assert set(decision) == {"status", "final_decision", "case_id", "reason"}
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_NOT_RECORDED"
    assert decision["reason"] == NOT_RECORDED
    assert str(uuid.UUID(decision["case_id"])) == decision["case_id"]
    assert str(tmp_path) not in json.dumps(decision)


def test_a_rejected_audit_insert_leaves_no_receipt_and_no_execute_safe_row(isolate_audit_db):
    run_script(isolate_audit_db, BASE_TABLES + "CREATE TRIGGER refuse BEFORE INSERT ON audit_log "
               "BEGIN SELECT RAISE(ABORT, 'refused'); END;")
    decision = submit(body())
    assert decision["final_decision"] == "ABORTED_NOT_RECORDED"
    assert str(isolate_audit_db) not in json.dumps(decision)
    assert table_rows(isolate_audit_db, "receipts") == []
    assert table_rows(isolate_audit_db, "audit_log") == []


def test_an_unrecorded_execute_safe_says_so_on_stderr_in_one_line_without_a_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path)
    assert submit(body())["final_decision"] == "ABORTED_NOT_RECORDED"
    captured = capsys.readouterr()
    assert len(captured.err.splitlines()) == 1
    assert captured.err.startswith("[boundary-validator]")
    assert str(tmp_path) not in captured.err
    assert captured.out == ""


# T6: the audit row and the receipt are written together or not at all


@pytest.mark.parametrize("script", [
    pytest.param(BASE_TABLES + "CREATE TRIGGER refuse BEFORE INSERT ON receipts "
                 "BEGIN SELECT RAISE(ABORT, 'refused'); END;", id="receipts-reject-the-insert"),
    pytest.param("CREATE TABLE receipts (unrelated TEXT);", id="receipts-without-its-columns"),
])
def test_a_receipt_that_cannot_be_inserted_leaves_neither_the_audit_row_nor_the_receipt(isolate_audit_db, gate, script):
    run_script(isolate_audit_db, script)
    decision = submit(body(Target_File=GOVERNED_TARGET, Topological_Grounding=OLD, Implementation_Block=NEW))
    assert decision["final_decision"] == "ABORTED_NOT_RECORDED"
    assert decision["reason"] == NOT_RECORDED
    assert table_rows(isolate_audit_db, "audit_log") == []
    assert table_rows(isolate_audit_db, "receipts") == []
    assert gate(*edit(OLD, NEW)) == 2


# D6: a refusal whose row cannot be written is returned as it is, and the failure is no longer silent


def test_a_refusal_whose_audit_row_cannot_be_written_is_returned_as_it_is_and_reported_on_stderr(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", tmp_path)
    decision = submit(body(Safety_Abort="BOUNDARY_VIOLATION"))
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"
    assert decision["status"] == "QUARANTINED"
    captured = capsys.readouterr()
    assert len(captured.err.splitlines()) == 1
    assert captured.err.startswith("[boundary-validator]")
    assert str(tmp_path) not in captured.err
    assert captured.out == ""


def test_a_refusal_whose_target_file_the_database_cannot_hold_is_returned_as_it_is_and_reported(
        isolate_audit_db, capsys):
    decision = submit(body(Safety_Abort="BOUNDARY_VIOLATION"), TARGET + SURROGATE)
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"
    captured = capsys.readouterr()
    assert len(captured.err.splitlines()) == 1
    assert captured.err.startswith("[boundary-validator]")
    assert table_rows(isolate_audit_db, "audit_log") == []


# T7: the texts that tell an agent how to build a proposal name the Rationale


BOUNDARY_VALIDATOR_SKILLS = [".claude/skills/boundary-validator/SKILL.md", ".opencode/skills/boundary-validator/SKILL.md"]
TDD_CYCLE_SKILLS = [".claude/skills/tdd-cycle/SKILL.md", ".opencode/skills/tdd-cycle/SKILL.md"]
IMPLEMENTER = ".claude/agents/implementer.md"


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def clause(number):
    match = re.search(rf"^{re.escape(number)} .*?(?={LF}{LF})", read("AGENTS.md"), re.S | re.M)
    assert match, number
    return match.group(0)


def test_the_model_has_the_rationale_as_a_property_and_agents_2_2_names_it():
    assert "Rationale" in AgentMutationProposal.model_fields
    assert "Rationale" in clause("2.2")


@pytest.mark.parametrize("path", BOUNDARY_VALIDATOR_SKILLS + TDD_CYCLE_SKILLS + [IMPLEMENTER])
def test_every_skill_and_the_implementer_that_tell_an_agent_how_to_build_a_proposal_name_the_rationale(path):
    assert "Rationale" in read(path)


def test_the_implementer_says_what_the_rationale_is_for():
    assert re.search("Rationale[^.]*[ ]why[ ]", read(IMPLEMENTER))


@pytest.mark.parametrize("path", BOUNDARY_VALIDATOR_SKILLS)
def test_the_boundary_validator_skill_has_the_rationale_in_its_description_and_the_new_outcome(path):
    text = read(path)
    description = [line for line in text.splitlines() if line.startswith("description:")]
    assert len(description) == 1
    assert "Rationale" in description[0]
    assert "ABORTED_NOT_RECORDED" in text


def test_every_property_of_the_model_is_named_in_agents_2_2_and_in_the_boundary_validator_skill():
    fields = set(AgentMutationProposal.model_fields)
    assert "Rationale" in fields
    for name in fields:
        assert name in clause("2.2"), name
        for path in BOUNDARY_VALIDATOR_SKILLS:
            assert name in read(path), (name, path)


def test_the_tool_description_and_the_model_docstring_name_the_rationale_and_the_new_outcome():
    assert "Rationale" in TOOL_DEFINITION["description"]
    assert "ABORTED_NOT_RECORDED" in TOOL_DEFINITION["description"]
    assert "Rationale" in AgentMutationProposal.__doc__


def test_none_of_those_texts_still_counts_the_fields_as_five_radicals():
    texts = {path: read(path) for path in BOUNDARY_VALIDATOR_SKILLS + TDD_CYCLE_SKILLS}
    texts["AGENTS.md"] = clause("2.2")
    texts["TOOL_DEFINITION"] = TOOL_DEFINITION["description"]
    texts["AgentMutationProposal"] = AgentMutationProposal.__doc__
    for name, text in texts.items():
        assert "5 Radicals" not in text, name


# T8: the hook reads a receipt planted with _persist_receipt exactly as before


def test_a_receipt_planted_with_persist_receipt_lets_the_hook_allow_exactly_its_edit(gate):
    assert gate(*edit(OLD, NEW)) == 2
    validator._persist_receipt(str(uuid.uuid4()), GOVERNED_TARGET, sha(OLD), sha(NEW))
    assert gate(*edit(OLD, NEW)) == 0
    assert gate(*edit(OLD, NEW + " ")) == 2
    assert gate(*edit(OLD + " ", NEW)) == 2
    assert gate(*edit(NEW, OLD)) == 2
    assert gate(*edit(OLD, NEW, str(REPO_ROOT / "src" / "b.txt"))) == 2
