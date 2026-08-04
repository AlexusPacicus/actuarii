"""
Structured Outputs contract (SEC-M-14..SEC-M-18).

Normative: docs/development/tests/SPEC-security.md
Coverage: SEC-M-14, SEC-M-15, SEC-M-16, SEC-M-17, SEC-M-18

RFC 2119: build_response_format MUST emit a strict json_schema response
format; strict mode MUST forbid additional properties; parse_proposal_json
MUST follow the ordered pipeline; repaired-but-incomplete JSON MUST raise
JSONParsingError; parse_proposal MUST validate against AgentMutationProposal
and the validator integration MUST keep SEC-M-01..12 outcomes intact.
"""
import json

import pytest

from traianus.security.schemas.parser import JSONParsingError, parse_proposal, parse_proposal_json
from traianus.security.schemas.proposals import AgentMutationProposal, build_response_format
from traianus.security.validator import validate_proposal


# ---------------------------------------------------------------------------
# SEC-M-14: build_response_format shape
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_14_shape():
    fmt = build_response_format(AgentMutationProposal)
    assert fmt["type"] == "json_schema"
    inner = fmt["json_schema"]
    assert inner["name"] == "AgentMutationProposal"
    assert inner["schema"] == AgentMutationProposal.model_json_schema()
    assert inner["strict"] is True


def test_structured_outputs_SEC_M_14_custom_name():
    fmt = build_response_format(AgentMutationProposal, name="TraianusProposal")
    assert fmt["json_schema"]["name"] == "TraianusProposal"


# ---------------------------------------------------------------------------
# SEC-M-15: strict invariants
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_15_strict_invariants():
    schema = AgentMutationProposal.model_json_schema()
    assert schema.get("additionalProperties") is False
    assert set(schema["required"]) == set(schema["properties"])


def test_structured_outputs_SEC_M_15_build_emits_strict_schema():
    fmt = build_response_format(AgentMutationProposal, strict=True)
    schema = fmt["json_schema"]["schema"]
    assert schema.get("additionalProperties") is False
    assert set(schema["required"]) == set(schema["properties"])


# ---------------------------------------------------------------------------
# SEC-M-16: parse_proposal_json ordered pipeline
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_16_pure_json_no_repair():
    raw = '{"Intent_Class": "FIX", "Target_File": "x", "Topological_Grounding": "y", "Implementation_Block": "z", "Safety_Abort": "NONE"}'
    parsed, used_repair = parse_proposal_json(raw)
    assert used_repair is False
    assert parsed["Intent_Class"] == "FIX"


def test_structured_outputs_SEC_M_16_fenced_json_extracted():
    raw = 'Here is the payload:\n```json\n{"Intent_Class": "FIX", "Target_File": "x", "Topological_Grounding": "y", "Implementation_Block": "z", "Safety_Abort": "NONE"}\n```\n'
    parsed, used_repair = parse_proposal_json(raw)
    assert used_repair is False
    assert parsed["Intent_Class"] == "FIX"


def test_structured_outputs_SEC_M_16_trailing_comma_repaired():
    raw = '{"Intent_Class": "FIX", "Target_File": "x", "Topological_Grounding": "y", "Implementation_Block": "z", "Safety_Abort": "NONE",}'
    parsed, used_repair = parse_proposal_json(raw)
    assert used_repair is True
    assert parsed["Intent_Class"] == "FIX"


# ---------------------------------------------------------------------------
# SEC-M-17: repaired-but-incomplete JSON raises JSONParsingError
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_17_repaired_incomplete_raises():
    raw = '{"Intent_Class": "FIX", "Target_File": "x"'  # truncated, repairable
    with pytest.raises(JSONParsingError):
        parse_proposal(raw)


# ---------------------------------------------------------------------------
# SEC-M-18: parse_proposal validation + validator integration intact
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_18_validates_agent_mutation_proposal():
    proposal = parse_proposal(
        json.dumps({
            "Intent_Class": "FIX",
            "Target_File": "traianus/app.py",
            "Topological_Grounding": "auto_calibrate_critical_threshold()",
            "Implementation_Block": "def f(): pass",
            "Safety_Abort": "NONE",
        })
    )
    assert isinstance(proposal, AgentMutationProposal)
    assert proposal.Intent_Class.value == "FIX"


def test_structured_outputs_SEC_M_18_invalid_json_still_invalid_decision():
    decision = validate_proposal("{not valid json")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_structured_outputs_SEC_M_18_safety_gate_still_blocks():
    decision = validate_proposal(
        json.dumps({
            "Intent_Class": "REFACTOR",
            "Implementation_Block": "dangerous",
            "Topological_Grounding": "x",
            "Safety_Abort": "RISK_HIGH",
        })
    )
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"
