"""The validator binds a receipt to one file and demands the literal quote whenever that file exists.

Normative: docs/process/PROCESO.md 3.2 (A02, A03, A12). The decision order is NUL, strict JSON,
primitives matrix, schema, Safety_Abort, target, quote, EXECUTE_SAFE.
"""
import json
import os
import sqlite3
from contextlib import closing

import pytest

from tools.boundary_validator import validator
from tools.boundary_validator.validator import handle_request, validate_proposal

INTENTS = ["FIX", "REFACTOR", "TEST", "DOC", "SPEC", "AUDIT"]
MUTATING = ["FIX", "REFACTOR", "AUDIT"]
FREE = ["TEST", "DOC", "SPEC"]
RADICALS = {"Intent_Class", "Target_File", "Topological_Grounding", "Implementation_Block", "Safety_Abort",
            "Rationale"}
CONTENT = "alpha beta gamma\n"


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    return tmp_path


def _proposal(intent="DOC", target="a.txt", quote="alpha", safety="NONE", block="text"):
    return json.dumps({
        "Intent_Class": intent,
        "Target_File": target,
        "Topological_Grounding": quote,
        "Implementation_Block": block,
        "Safety_Abort": safety,
        "Rationale": "A test proposal.",
    })


def _decisions(audit_db):
    with closing(sqlite3.connect(audit_db)) as conn:
        return conn.execute("SELECT decision, target_file FROM audit_log").fetchall()


def _call(arguments, request_id=1):
    return handle_request({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                           "params": {"name": "validate_proposal", "arguments": arguments}})


def _refs(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref":
                yield value
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


# ---------------------------------------------------------------------------
# Target (A03)
# ---------------------------------------------------------------------------


def test_a_missing_target_file_is_a_mismatch_and_is_logged(root, isolate_audit_db):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    decision = validate_proposal(_proposal())
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_TARGET_MISMATCH"
    assert _decisions(isolate_audit_db) == [("ABORTED_TARGET_MISMATCH", "")]


def test_another_file_is_a_mismatch_and_is_logged(root, isolate_audit_db):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    (root / "b.txt").write_text(CONTENT, encoding="utf-8")
    decision = validate_proposal(_proposal(target="a.txt"), "b.txt")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_TARGET_MISMATCH"
    assert _decisions(isolate_audit_db) == [("ABORTED_TARGET_MISMATCH", "b.txt")]


def test_a_mismatch_between_files_that_do_not_exist_is_still_a_mismatch(root):
    decision = validate_proposal(_proposal(target="new/a.txt"), "new/b.txt")
    assert decision["final_decision"] == "ABORTED_TARGET_MISMATCH"


@pytest.mark.parametrize("intent", INTENTS)
def test_a_mismatch_is_denied_whatever_the_intent(root, intent):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    decision = validate_proposal(_proposal(intent=intent, target="a.txt"), "c.txt")
    assert decision["final_decision"] == "ABORTED_TARGET_MISMATCH"


def test_a_relative_path_and_the_absolute_one_of_the_same_file_match(root, tmp_path_factory, monkeypatch):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    assert validate_proposal(_proposal(target="a.txt"), str(root / "a.txt"))["final_decision"] == "EXECUTE_SAFE"
    assert validate_proposal(_proposal(target=str(root / "a.txt")), "a.txt")["final_decision"] == "EXECUTE_SAFE"


def test_a_relative_path_is_resolved_against_the_root_not_the_cwd(root, tmp_path_factory, monkeypatch):
    (root / "sub").mkdir()
    (root / "sub" / "a.txt").write_text(CONTENT, encoding="utf-8")
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))
    assert validate_proposal(_proposal(target="sub/../sub/a.txt"), "sub/a.txt")["final_decision"] == "EXECUTE_SAFE"


def test_two_names_of_one_existing_file_match(root):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    os.link(root / "a.txt", root / "b.txt")
    assert validate_proposal(_proposal(target="a.txt"), "b.txt")["final_decision"] == "EXECUTE_SAFE"


def test_two_files_with_the_same_content_do_not_match(root):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    (root / "b.txt").write_text(CONTENT, encoding="utf-8")
    assert validate_proposal(_proposal(target="a.txt"), "b.txt")["final_decision"] == "ABORTED_TARGET_MISMATCH"


def test_a_malformed_proposal_keeps_its_decision_before_the_target_check(root):
    malformed = json.dumps({"Intent_Class": "DOC", "Target_File": "a.txt"})
    assert validate_proposal(malformed, "b.txt")["final_decision"] == "INVALID_JSON"
    assert validate_proposal(malformed)["final_decision"] == "INVALID_JSON"


def test_a_safety_abort_keeps_its_decision_before_the_target_check(root):
    decision = validate_proposal(_proposal(target="a.txt", safety="BOUNDARY_VIOLATION"), "b.txt")
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"


# ---------------------------------------------------------------------------
# Quote (A02)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("intent", INTENTS)
def test_an_existing_file_needs_the_literal_quote_whatever_the_intent(root, intent):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    missing = validate_proposal(_proposal(intent=intent, quote="this quote is nowhere"), "a.txt")
    assert missing["status"] == "QUARANTINED"
    assert missing["final_decision"] == "ABORTED_GROUNDING_FAILED"
    present = validate_proposal(_proposal(intent=intent, quote="beta gamma"), "a.txt")
    assert present["status"] == "VALIDATED"
    assert present["final_decision"] == "EXECUTE_SAFE"


@pytest.mark.parametrize("intent", INTENTS)
def test_an_empty_quote_does_not_ground_a_file_with_content(root, intent):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    assert validate_proposal(_proposal(intent=intent, quote=""), "a.txt")["final_decision"] == "ABORTED_GROUNDING_FAILED"


@pytest.mark.parametrize("intent", INTENTS)
def test_an_empty_existing_file_admits_only_the_empty_quote(root, intent):
    (root / "a.txt").write_bytes(b"")
    assert validate_proposal(_proposal(intent=intent, quote=""), "a.txt")["final_decision"] == "EXECUTE_SAFE"
    assert validate_proposal(_proposal(intent=intent, quote="x"), "a.txt")["final_decision"] == "ABORTED_GROUNDING_FAILED"


@pytest.mark.parametrize("intent", FREE)
def test_a_file_that_does_not_exist_needs_no_quote_for_test_doc_and_spec(root, intent):
    for quote in ("", "nothing to cite in a new file"):
        decision = validate_proposal(_proposal(intent=intent, target="new/a.txt", quote=quote), "new/a.txt")
        assert decision["final_decision"] == "EXECUTE_SAFE", quote


@pytest.mark.parametrize("intent", MUTATING)
def test_a_file_that_does_not_exist_fails_grounding_for_fix_refactor_and_audit(root, intent):
    decision = validate_proposal(_proposal(intent=intent, target="new/a.txt", quote=""), "new/a.txt")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


@pytest.mark.parametrize("intent", INTENTS)
def test_the_target_stays_inside_the_root(root, intent, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "a.txt"
    outside.write_text(CONTENT, encoding="utf-8")
    decision = validate_proposal(_proposal(intent=intent, target=str(outside)), str(outside))
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


@pytest.mark.parametrize("intent", FREE)
def test_a_new_file_outside_the_root_is_denied(root, intent, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "new.txt"
    decision = validate_proposal(_proposal(intent=intent, target=str(outside)), str(outside))
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


# ---------------------------------------------------------------------------
# MCP (A12)
# ---------------------------------------------------------------------------


def _published_schema():
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    return response["result"]["tools"][0]["inputSchema"]


def test_the_published_schema_declares_the_proposal_as_the_strict_object():
    schema = _published_schema()
    proposal = schema["properties"]["proposal"]
    assert proposal["type"] == "object"
    assert proposal["additionalProperties"] is False
    assert set(proposal["properties"]) == RADICALS
    assert set(proposal["required"]) == RADICALS


def test_the_published_schema_requires_a_target_file_string():
    schema = _published_schema()
    assert schema["properties"]["target_file"]["type"] == "string"
    assert schema["required"] == ["proposal", "target_file"]


def test_every_reference_of_the_published_schema_resolves_in_it():
    schema = _published_schema()
    refs = set(_refs(schema))
    assert refs
    for ref in refs:
        assert ref.startswith("#/$defs/"), ref
        assert ref.removeprefix("#/$defs/") in schema["$defs"], ref


def test_the_description_lists_the_decisions_including_the_target_mismatch():
    description = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"][0]["description"]
    for decision in ("EXECUTE_SAFE", "ABORTED_GROUNDING_FAILED", "ABORTED_VIOLATES_ZERO_TRUST",
                     "BLOCKED_BY_SAFETY_GATE", "INVALID_JSON", "ABORTED_TARGET_MISMATCH"):
        assert decision in description


def test_a_proposal_as_text_is_an_invalid_params_error():
    response = _call({"proposal": _proposal(), "target_file": "a.txt"})
    assert response["error"]["code"] == -32602
    assert "proposal" in response["error"]["message"]


def test_a_missing_proposal_is_an_invalid_params_error():
    response = _call({"target_file": "a.txt"})
    assert response["error"]["code"] == -32602
    assert "proposal" in response["error"]["message"]


@pytest.mark.parametrize("arguments", [
    {"proposal": json.loads(_proposal())},
    {"proposal": json.loads(_proposal()), "target_file": ""},
    {"proposal": json.loads(_proposal()), "target_file": 7},
    {"proposal": json.loads(_proposal()), "target_file": None},
], ids=["missing", "empty", "number", "null"])
def test_a_missing_or_non_string_target_file_is_an_invalid_params_error(arguments):
    response = _call(arguments)
    assert response["error"]["code"] == -32602
    assert "target_file" in response["error"]["message"]


def test_a_proposal_object_is_validated_like_its_text(root):
    (root / "a.txt").write_text(CONTENT, encoding="utf-8")
    response = _call({"proposal": json.loads(_proposal()), "target_file": "a.txt"})
    assert "error" not in response
    assert json.loads(response["result"]["content"][0]["text"])["final_decision"] == "EXECUTE_SAFE"
    response = _call({"proposal": json.loads(_proposal()), "target_file": "b.txt"})
    assert json.loads(response["result"]["content"][0]["text"])["final_decision"] == "ABORTED_TARGET_MISMATCH"
