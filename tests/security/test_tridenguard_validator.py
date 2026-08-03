"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
TridenGuard Zero-Trust gate (SEC-M-01..06): validate_proposal and its
MCP server over stdio JSON-RPC.
Normative: docs/development/tests/SPEC-security.md
Coverage: SEC-M-01, SEC-M-02, SEC-M-03, SEC-M-04, SEC-M-05, SEC-M-06, SEC-M-07"""
import json
import subprocess
import sys
from pathlib import Path

from tools.tridenguard_validator import validate_proposal

ROOT = Path(__file__).resolve().parents[2]


def _grounded_proposal() -> str:
    return json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "update threshold",
        "Topological_Grounding": "auto_calibrate_critical_threshold()",
        "Safety_Abort": "NONE",
    })


def test_security_SEC_M_01_invalid_json_rejected():
    decision = validate_proposal("{not valid json")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "INVALID_JSON"


def test_security_SEC_M_02_safety_abort_blocks():
    proposal = json.dumps({
        "Intent_Class": "REFACTOR",
        "Implementation_Block": "dangerous change",
        "Topological_Grounding": "x",
        "Safety_Abort": "RISK_HIGH",
    })
    decision = validate_proposal(proposal)
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"


def test_security_SEC_M_03_external_network_blocked():
    for token in ["fetch(", "axios", "urllib.request", "import requests"]:
        proposal = json.dumps({
            "Intent_Class": "REFACTOR",
            "Implementation_Block": f"const x = {token}('http://evil');",
            "Topological_Grounding": "x",
            "Safety_Abort": "NONE",
        })
        decision = validate_proposal(proposal)
        assert decision["status"] == "QUARANTINED", token
        assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST", token


def test_security_SEC_M_04_literal_grounding_required():
    src = (ROOT / "traianus" / "app.py").read_text(encoding="utf-8")
    assert "auto_calibrate_critical_threshold()" in src  # cita existe literal

    proposal = _grounded_proposal()
    # Grounding que NO existe literalmente en el archivo objetivo
    proposal_bad = json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "update threshold",
        "Topological_Grounding": "esta_cita_no_existe_en_el_codigo_xyz",
        "Safety_Abort": "NONE",
    })
    decision = validate_proposal(proposal_bad, str(ROOT / "traianus" / "app.py"))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


def test_security_SEC_M_05_valid_grounding_approved():
    decision = validate_proposal(_grounded_proposal(), str(ROOT / "traianus" / "app.py"))
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"
    assert decision["and_gate_ok"] is True


def test_security_SEC_M_07_mutating_intent_requires_target_file():
    """SEC-M-07: REFACTOR/FIX/AUDIT without a target_file must NOT pass
    (no fail-open). The tool schema documents target_file as 'required for
    REFACTOR/FIX/AUDIT'; omitting it is a grounding failure."""
    for intent in ("REFACTOR", "FIX", "AUDIT"):
        proposal = json.dumps({
            "Intent_Class": intent,
            "Implementation_Block": "update threshold",
            "Topological_Grounding": "auto_calibrate_critical_threshold()",
            "Safety_Abort": "NONE",
        })
        decision = validate_proposal(proposal)
        assert decision["status"] == "QUARANTINED", intent
        assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED", intent


def test_security_SEC_M_07_unreadable_target_file_is_grounding_failure():
    """SEC-M-07: a mutating intent whose target_file does not exist is also
    a grounding failure (the file cannot be verified)."""
    proposal = _grounded_proposal()
    decision = validate_proposal(proposal, "/nonexistent/path/to/app.py")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


def test_security_SEC_M_06_mcp_stdio_jsonrpc():
    script = str(ROOT / "tools" / "tridenguard_validator.py")
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"clientInfo": {"name": "test", "version": "0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "validate_proposal",
                    "arguments": {"proposal": _grounded_proposal(),
                                  "target_file": str(ROOT / "traianus" / "app.py")}}},
    ]
    payload = "".join(json.dumps(m) + "\n" for m in messages)
    proc = subprocess.run(
        [sys.executable, script],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )
    # The stdout channel is not corrupted: one valid JSON-RPC response per line.
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    assert len(lines) == 3, f"expected 3 responses, got {len(lines)}"
    for line, expected_id in zip(lines, (1, 2, 3)):
        resp = json.loads(line)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == expected_id
        assert "result" in resp and "error" not in resp
    init_result = json.loads(lines[0])["result"]
    assert init_result["serverInfo"]["name"] == "tridenguard-validator"
    tools = json.loads(lines[1])["result"]["tools"]
    assert tools[0]["name"] == "validate_proposal"
    call_result = json.loads(lines[2])["result"]["content"][0]["text"]
    assert "EXECUTE_SAFE" in call_result
