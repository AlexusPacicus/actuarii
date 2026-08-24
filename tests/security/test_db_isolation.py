"""Gate-hardening regressions (session remediation v1.0.0-post).

Two independent defects are pinned here:

1. DB isolation: `traianus.security.validator` must resolve the database
   path LAZILY (via `storage.DB_PATH` at call time). An import-time binding
   (`from traianus.storage import DB_PATH`) copies the default value before
   the autouse `isolate_db` fixture can monkeypatch it, redirecting every
   `validate_proposal()` audit write into the real repo-root `traianus.db`.

2. Strict schema conformance (AGENTS.md 5.1): `validate_proposal()` must
   enforce the normative `AgentMutationProposal` contract. Today an empty
   payload `{}` or an invented `Intent_Class` (e.g. "HACK") returns
   EXECUTE_SAFE, skipping the mandatory literal-grounding gate.
"""
import json
import sqlite3

# Module-level import mirrors the committed security suites: the validator
# binds DB state at collection time, before any autouse fixture can patch it.
from traianus.security.validator import validate_proposal


def test_audit_persists_to_isolated_db(isolate_db):
    decision = validate_proposal(
        '{"Intent_Class":"DOC","Target_File":"docs/x.md",'
        '"Topological_Grounding":"q","Implementation_Block":"b","Safety_Abort":"NONE"}'
    )
    assert decision["final_decision"] == "EXECUTE_SAFE"
    with sqlite3.connect(isolate_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    assert count >= 1


def test_empty_payload_rejected_as_invalid_json():
    from traianus.security.validator import validate_proposal

    decision = validate_proposal("{}")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_unknown_intent_class_cannot_skip_grounding():
    """An Intent_Class outside the canonical enum MUST be rejected even when
    the block carries no forbidden token and the grounding quote is absent."""
    from traianus.security.validator import validate_proposal

    decision = validate_proposal(json.dumps({
        "Intent_Class": "HACK",
        "Target_File": "docs/x.md",
        "Topological_Grounding": "esta-cota-no-existe-en-ningun-archivo",
        "Implementation_Block": "print('hola')",
        "Safety_Abort": "NONE",
    }))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_extra_fields_rejected_strict_schema():
    """extra="forbid": payloads outside the 5 Radicals are quarantined."""
    from traianus.security.validator import validate_proposal

    decision = validate_proposal(json.dumps({
        "Intent_Class": "DOC",
        "Target_File": "docs/x.md",
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
        "injected": "field",
    }))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_non_dict_payload_rejected_as_invalid_json():
    from traianus.security.validator import validate_proposal

    decision = validate_proposal("[1, 2, 3]")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_denylist_still_precedes_schema_for_malformed_payloads():
    """Content screening keeps priority: forbidden tokens quarantine even
    when the payload also violates the strict schema."""
    from traianus.security.validator import validate_proposal

    decision = validate_proposal(json.dumps({
        "Intent_Class": "NONE",
        "Implementation_Block": "socket.socket()",
        "Topological_Grounding": "",
        "Safety_Abort": "NONE",
    }))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST"
