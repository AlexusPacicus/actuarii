"""
Structured Outputs contract (SEC-M-14..SEC-M-18).

Normative: tools/boundary_validator/schemas/proposals.py (AgentMutationProposal)
Coverage: SEC-M-14, SEC-M-15, SEC-M-16, SEC-M-17, SEC-M-18

RFC 2119: build_response_format MUST emit a strict json_schema response
format; strict mode MUST forbid additional properties; the validator MUST
read the proposal with a strict JSON parse and MUST NOT extract or repair
it (an invalid payload is INVALID_JSON); the validator integration MUST
keep SEC-M-01..12 outcomes intact.
"""
import json
from pathlib import Path

import pytest

from tools.boundary_validator import schemas
from tools.boundary_validator.schemas.proposals import AgentMutationProposal, build_response_format
from tools.boundary_validator.validator import validate_proposal

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "tools" / "boundary_validator" / "schemas"
TARGET = "docs/strict-input-probe.md"
VALID = (
    '{"Intent_Class": "DOC", "Target_File": "docs/strict-input-probe.md", "Topological_Grounding": "y", '
    '"Implementation_Block": "z", "Safety_Abort": "NONE"}'
)


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
# SEC-M-16/17: the proposal is read with a strict parse; nothing is extracted or repaired
# ---------------------------------------------------------------------------


def test_structured_outputs_SEC_M_16_a_valid_object_is_accepted():
    decision = validate_proposal(VALID, TARGET)
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"


STRICT_REJECTIONS = {
    "fenced block": "```json\n" + VALID + "\n```",
    "text around the object": "Here is the payload:\n" + VALID + "\nThat is all.",
    "trailing comma": VALID[:-1] + ",}",
    "unclosed brace": VALID[:-1],
    "truncated": '{"Intent_Class": "DOC", "Target_File": "docs/strict-input-probe.md"',
    "duplicate key": VALID[:-1] + ', "Intent_Class": "FIX"}',
    "NaN": VALID[:-1] + ', "Extra": NaN}',
    "Infinity": VALID[:-1] + ', "Extra": Infinity}',
    "negative Infinity": VALID[:-1] + ', "Extra": -Infinity}',
    "array": "[" + VALID + "]",
    "string": json.dumps(VALID),
    "null": "null",
    "number": "42",
    "empty": "",
    "single quotes": VALID.replace('"', "'"),
}


@pytest.mark.parametrize("raw", STRICT_REJECTIONS.values(), ids=STRICT_REJECTIONS.keys())
def test_structured_outputs_SEC_M_17_anything_but_a_strict_object_is_invalid_json(raw):
    decision = validate_proposal(raw, TARGET)
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_structured_outputs_SEC_M_17_a_duplicate_key_does_not_let_the_last_value_win():
    first_wins = VALID[:-1] + ', "Intent_Class": "DOC"}'
    assert validate_proposal(first_wins, TARGET)["final_decision"] == "INVALID_JSON"


def test_structured_outputs_SEC_M_17_deeply_nested_input_is_invalid_json():
    assert validate_proposal("[" * 100000, TARGET)["final_decision"] == "INVALID_JSON"


@pytest.mark.parametrize("module", ["parser", "docstate"])
def test_structured_outputs_SEC_M_17_the_tolerant_parser_and_docstate_modules_are_gone(module):
    assert not (SCHEMAS_DIR / f"{module}.py").exists()
    with pytest.raises(ImportError):
        __import__(f"tools.boundary_validator.schemas.{module}")


@pytest.mark.parametrize("name", ["DocState", "JSONParsingError", "parse_proposal", "parse_proposal_json"])
def test_structured_outputs_SEC_M_17_the_package_no_longer_exports_them(name):
    assert name not in schemas.__all__
    assert not hasattr(schemas, name)


# ---------------------------------------------------------------------------
# SEC-M-18: validator integration intact
# ---------------------------------------------------------------------------


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
