"""Internal-error masking regression (audit M4-medium).

Six endpoints answered 5xx with `detail=str(e)`, leaking exception internals
(traceback fragments, SQL messages) to the client. Contract: every unhandled
exception maps to a fixed generic detail; internals stay in server logs.
"""
import numpy as np
import pytest

import traianus.storage as storage

MARKER = "INTERNAL_MARKER_X9"
GENERIC = "Internal server error."


def _fake_axes() -> list[tuple]:
    blob = np.ones(384, dtype=np.float64).tobytes()
    return [("AXIS_1", "\u25b2", "_SOMETHING", blob)]


def test_nodos_masks_internal_error(client, auth_headers, monkeypatch):
    def boom():
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "get_current_nodes", boom)
    r = client.get("/nodos")
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC


def test_telemetry_masks_internal_error(client, auth_headers, monkeypatch):
    def boom():
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "get_telemetry_errors", boom)
    r = client.get("/telemetry", headers=auth_headers)
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC


def test_relations_get_masks_internal_error(client, auth_headers, monkeypatch):
    def boom():
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "get_current_edges", boom)
    r = client.get("/relations", headers=auth_headers)
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC


def test_consolidar_masks_internal_error(client, auth_headers, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "node_exists", lambda conn, nid: True)
    monkeypatch.setattr(storage, "insert_node_revision", boom)
    r = client.post(
        "/nodos/NODE_1/consolidar",
        json={"text": "consolidation probe", "ethical_key": True},
        headers=auth_headers,
    )
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC


def test_relations_post_masks_internal_error(client, auth_headers, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "node_exists", lambda conn, nid: True)
    monkeypatch.setattr(storage, "insert_edge_revision", boom)
    r = client.post(
        "/relations",
        json={"source": "NODE_1", "target": "NODE_2", "state": "manual"},
        headers=auth_headers,
    )
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC


def test_mutate_masks_internal_error(client, auth_headers, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError(MARKER)

    monkeypatch.setattr(storage, "get_active_epoch_axes", _fake_axes)
    monkeypatch.setattr(storage, "insert_axis", boom)
    r = client.post("/mutate/%CE%A9", headers=auth_headers)
    assert r.status_code == 500
    assert MARKER not in r.text
    assert r.json()["detail"] == GENERIC
