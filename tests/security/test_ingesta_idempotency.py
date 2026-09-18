"""R3/R4 (REMEDIATION-01 Delta2): idempotency-key enforcement on both
ingestion endpoints -- a missing X-Idempotency-Key must be rejected, not
treated as "no key" (AGENTS.md §2.3, spec §3.1)."""


def test_ingesta_rejects_missing_idempotency_key(client, auth_headers):
    resp = client.post(
        "/ingesta",
        content=b"hola mundo",
        headers={"Content-Type": "text/plain", **auth_headers},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("idempotency" in str(err.get("loc", "")).lower() for err in detail)


def test_ingesta_vector_enforces_idempotency_key(client, auth_headers):
    resp = client.post(
        "/ingesta/vector",
        json={"vector": [0.1] * 384},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("idempotency" in str(err.get("loc", "")).lower() for err in detail)
