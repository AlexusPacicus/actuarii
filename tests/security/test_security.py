"""
Zero-Trust Perimeter and Boundary-Validator Gateway.
Covers: Token authentication, enumerated CORS, ingress allowlist, and Boundary-Validator gateway.
"""
import json
import pytest
from traianus.security.validator import validate_proposal

def test_zero_trust_ingress_allowlist(client, ingesta, auth_headers):
    """Rechaza payloads cuyo Content-Type no sea text/plain con HTTP 415."""
    res_bad = client.post(
        "/ingesta",
        content="{}".encode("utf-8"),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert res_bad.status_code == 415

    res_good = ingesta("ok")
    assert res_good.status_code == 200

def test_ingesta_rejects_null_bytes(client, auth_headers):
    """Null byte (\x00) en el cuerpo -> 400 (verificación a nivel de byte, §3.4 P1)."""
    res = client.post(
        "/ingesta",
        content=b"valid\x00text",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert res.status_code == 400

def test_ingesta_rejects_invalid_utf8(client, auth_headers):
    """Decodificación estricta UTF-8 fallida -> 400 (§3.4 P1)."""
    res = client.post(
        "/ingesta",
        content=b"\xff\xfe\xfd",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert res.status_code == 400

def test_ingesta_idempotency_returns_same_id(client, ingesta):
    """X-Idempotency-Key: reintento devuelve el mismo ingestion_id (A-c, §3.3)."""
    first = ingesta("idempotent note", idempotency_key="k-1")
    second = ingesta("idempotent note", idempotency_key="k-1")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["ingestion_id"] == second.json()["ingestion_id"]

def test_protected_routes_require_token(client):
    """Rutas mutantes devuelven 401 si falta el header x-traianus-token."""
    res = client.post(
        "/ingesta",
        content="unauthorized".encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )
    assert res.status_code == 401

def test_boundary_validator_gate():
    """Validación Zero-Trust de propuestas (5 Radicales)."""
    valid_prop = json.dumps({
        "Intent_Class": "FIX",
        "Implementation_Block": "x = 1",
        "Topological_Grounding": "auto_calibrate_critical_threshold()",
        "Safety_Abort": "NONE"
    })
    decision = validate_proposal(valid_prop, "traianus/app.py")
    assert decision["status"] == "VALIDATED"
    assert decision["final_decision"] == "EXECUTE_SAFE"

def test_ingesta_rejects_overlong_utf8(client, auth_headers):
    """Overlong UTF-8 lead bytes (C0/C1) must be rejected at the byte level."""
    res = client.post(
        "/ingesta",
        content=b"\xc0\xaf",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert res.status_code == 400

def test_ingesta_rejects_utf16_bom(client, auth_headers):
    """UTF-16 BOM bytes must be rejected as non-UTF-8."""
    res = client.post(
        "/ingesta",
        content=b"\xff\xfeH\x00i\x00",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert res.status_code == 400

def test_ingesta_rejects_null_byte_at_end(client, auth_headers):
    """A trailing null byte must still trigger the null-byte rejection."""
    res = client.post(
        "/ingesta",
        content=b"valid\x00",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert res.status_code == 400

def test_ingesta_accepts_multi_byte_utf8_without_false_positive(client, ingesta):
    """Valid multi-byte UTF-8 must pass the perimeter (no false positive)."""
    res = ingesta("Español ñ ¡¿ç — 你好 🚀")
    assert res.status_code == 200

def test_ingesta_accepts_charset_parameter(client, ingesta):
    """text/plain with a charset parameter must be accepted (allowlist base type)."""
    res = ingesta("charset ok", content_type="text/plain; charset=utf-8")
    assert res.status_code == 200
