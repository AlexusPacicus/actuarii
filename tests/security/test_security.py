"""
Boundary-Validator gateway (Zero-Trust gate over proposals).
"""
import json
from pathlib import Path

from tools.boundary_validator.validator import validate_proposal

ROOT = Path(__file__).resolve().parents[2]


def test_boundary_validator_gate():
    """Zero-Trust validation of proposals."""
    valid_prop = json.dumps({
        "Intent_Class": "FIX",
        "Target_File": str(ROOT / "tools" / "boundary_validator" / "validator.py"),
        "Implementation_Block": "x = 1",
        "Topological_Grounding": "def validate_proposal(",
        "Safety_Abort": "NONE",
        "Rationale": "A test proposal."
    })
    decision = validate_proposal(valid_prop, str(ROOT / "tools" / "boundary_validator" / "validator.py"))
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"
