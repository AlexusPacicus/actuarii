"""
Boundary-Validator gateway (Zero-Trust gate over 5-Radicals proposals).
"""
import json
from pathlib import Path

from tools.boundary_validator.validator import validate_proposal

ROOT = Path(__file__).resolve().parents[2]


def test_boundary_validator_gate():
    """Validación Zero-Trust de propuestas (5 Radicales)."""
    valid_prop = json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "x = 1",
        "Topological_Grounding": "def validate_proposal(",
        "Safety_Abort": "NONE"
    })
    decision = validate_proposal(valid_prop, str(ROOT / "tools" / "boundary_validator" / "validator.py"))
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"
