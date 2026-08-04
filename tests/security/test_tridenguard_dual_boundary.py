"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Dual Boundary Pattern (SEC-M-08..12): canonical path containment (`..`
traversal / symlinks resolved), `\x00` sanitization, expanded network-token
denylist, UTF-8 binary subsequence grounding over `read_bytes()`, and silent
denial (no target path / OS details leaked). RED phase: every test asserts
the NEW behavior that the current validator does NOT yet implement; the
validator (`traianus/security/validator.py`) is intentionally untouched here
and will be refactored in Phase 4.
Normative: docs/development/tests/SPEC-security.md
Coverage: SEC-M-08, SEC-M-09, SEC-M-10, SEC-M-11, SEC-M-12"""
import json
from pathlib import Path

from traianus.security.validator import validate_proposal

GROUNDING_MARKER = "dual_boundary_victim_marker"


def _grounded_proposal() -> str:
    return json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "update threshold",
        "Topological_Grounding": GROUNDING_MARKER,
        "Safety_Abort": "NONE",
    })


def _noop_proposal(block: str) -> str:
    return json.dumps({
        "Intent_Class": "NONE",
        "Implementation_Block": block,
        "Topological_Grounding": "",
        "Safety_Abort": "NONE",
    })


def test_security_SEC_M_08_target_outside_repo_root(tmp_path):
    """SEC-M-08: a target_file outside the authorized repository root MUST
    NOT pass the grounding gate (path containment); the validator must
    return ABORTED_GROUNDING_FAILED."""
    victim = tmp_path / "victim.txt"
    victim.write_text(GROUNDING_MARKER, encoding="utf-8")
    decision = validate_proposal(_grounded_proposal(), str(victim))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


def test_security_SEC_M_08_symlink_escape(tmp_path):
    """SEC-M-08: a symlink whose canonical (resolved) target lies outside the
    authorized repository root MUST NOT pass the grounding gate."""
    victim = tmp_path / "victim.txt"
    victim.write_text(GROUNDING_MARKER, encoding="utf-8")
    link = tmp_path / "escape.txt"
    link.symlink_to(victim)
    decision = validate_proposal(_grounded_proposal(), str(link))
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


def test_security_SEC_M_08_traversal_parent_dot_dot(monkeypatch, tmp_path):
    """SEC-M-08: a `..` traversal (sub/../victim.txt) MUST be canonicalized;
    the resolved path lies outside the authorized root and MUST NOT pass."""
    victim = tmp_path / "victim.txt"
    victim.write_text(GROUNDING_MARKER, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    monkeypatch.chdir(tmp_path)
    decision = validate_proposal(_grounded_proposal(), "sub/../victim.txt")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"


def test_security_SEC_M_09_null_byte_in_implementation_block():
    """SEC-M-09: a `\x00` in Implementation_Block (JSON-escaped \u0000) MUST
    be rejected silently before processing."""
    proposal = json.dumps({
        "Intent_Class": "NONE",
        "Implementation_Block": "import req\u0000uests",
        "Topological_Grounding": "",
        "Safety_Abort": "NONE",
    })
    decision = validate_proposal(proposal)
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST"


def test_security_SEC_M_09_null_byte_in_target_file():
    """SEC-M-09: a `\x00` in the target_file path MUST be rejected as a
    QUARANTINED dict — never an uncaught ValueError."""
    decision = validate_proposal(_grounded_proposal(), "app\x00.py")
    assert isinstance(decision, dict)
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST"


def test_security_SEC_M_10_expanded_network_tokens():
    """SEC-M-10: fragments with httpx/socket/urllib3/subprocess/curl/wget/
    aiohttp/importlib/os.system/requests. MUST NOT pass the Zero-Trust Gate."""
    probes = [
        "httpx.get('http://evil.example')",
        "socket.socket()",
        "urllib3.request('http://evil.example')",
        "subprocess.run(['curl', 'http://evil.example'])",
        "importlib.import_module('requests')",
        "os.system('curl http://evil.example')",
    ]
    for token in probes:
        decision = validate_proposal(_noop_proposal(token))
        assert decision["status"] == "QUARANTINED", token
        assert decision["final_decision"] == "ABORTED_VIOLATES_ZERO_TRUST", token


def test_security_SEC_M_11_non_utf8_file_no_crash(tmp_path):
    """SEC-M-11: grounding is a UTF-8 binary subsequence over read_bytes();
    a non-UTF-8 target file MUST fail closed (dict, QUARANTINED) and never
    crash the gate with UnicodeDecodeError."""
    src = tmp_path / "non_utf8.py"
    src.write_bytes(b"def caf\xe9(): pass\n")
    proposal = json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "update threshold",
        "Topological_Grounding": "café",
        "Safety_Abort": "NONE",
    })
    decision = validate_proposal(proposal, str(src))
    assert isinstance(decision, dict)
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] in {
        "ABORTED_GROUNDING_FAILED",
        "ABORTED_VIOLATES_ZERO_TRUST",
    }


def test_security_SEC_M_12_silent_denial_no_path_leak():
    """SEC-M-12: grounding failures MUST be silent — the decision MUST NOT
    contain the target path or OS details — and every decision keeps
    status + final_decision."""
    decision = validate_proposal(_grounded_proposal(), "/nonexistent/path/to/app.py")
    assert decision["status"] == "QUARANTINED"
    assert decision["final_decision"] == "ABORTED_GROUNDING_FAILED"
    reason = decision.get("reason", "")
    assert "/nonexistent" not in reason
    assert "app.py" not in reason
