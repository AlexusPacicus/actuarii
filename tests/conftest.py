"""
Root test harness configuration (Phase 0: Foundations).

Shared fixtures that ELIMINATE the DDL and isolation duplication that
existed in the 34 pre-Phase 0 tests (two byte-for-byte copies of the same schema):
- `operator_token_env` (autouse): TRAIANUS_TOKEN for protected routes (H3).
- `isolate_db` (autouse): ephemeral SQLite DB per test, single DDL via
  `helpers/db_factory.create_test_db`, monkeypatch of `traianus.storage.DB_PATH`.
- `client`: TestClient of FastAPI over the real app.
- `auth_headers`: valid operator header.
- `_hermetic_model` (autouse): injects a fake encoder (L1) into all
  tests except those marked `@pytest.mark.model` (E2E with real model).
"""
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT, TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import traianus.app as main  # noqa: E402
import traianus.bootstrap as bootstrap  # noqa: E402
import traianus.storage as storage  # noqa: E402
from helpers.db_factory import create_test_db  # noqa: E402
from helpers.fake_encoder import FakeSentenceTransformer  # noqa: E402

AUTH_TOKEN = "test-operator-token"


@pytest.fixture(autouse=True)
def operator_token_env(monkeypatch):
    """Sets TRAIANUS_TOKEN for protected routes (H3). Fail-closed:
    without this env, require_token rejects with 401."""
    monkeypatch.setenv("TRAIANUS_TOKEN", AUTH_TOKEN)
    yield
    monkeypatch.undo()


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """
    Ephemeral SQLite DB per test with the canonical schema (single DDL in
    helpers/db_factory.py). Replaces the two duplicated fixtures
    pre-Phase 0 (test_control_plane.isolate_test_database and
    test_append_only_log.isolate_append_only_db).
    """
    test_db_path = str(tmp_path / "test_traianus.db")
    # ADR-025 §2.1: DB_PATH lives in the storage package; get_db_connection()
    # resolves it lazily, so a single patch takes effect globally.
    monkeypatch.setattr(storage, "DB_PATH", test_db_path)
    create_test_db(test_db_path, seed="onehot")
    return test_db_path


@pytest.fixture
def client():
    """HTTP test client over the real FastAPI app."""
    return TestClient(main.app)


@pytest.fixture
def auth_headers():
    """Valid operator header (X-Traianus-Token)."""
    return {"X-Traianus-Token": AUTH_TOKEN}


@pytest.fixture
def ingesta(client, auth_headers):
    """
    Shared raw `text/plain` ingestion helper (SPEC-REFACTOR-v0.2 §3.4).

    Migrates the repeated `client.post("/ingesta", json={"type": ...})`
    call sites to the v0.2 contract: raw UTF-8 body + `Content-Type` header
    (the MIME allowlist moved from the JSON `type` field to the header) +
    optional `X-Idempotency-Key`.
    """
    def _ingesta(
        text: str,
        content_type: str = "text/plain",
        idempotency_key: str | None = None,
        use_auth: bool = True,
    ):
        headers = {"Content-Type": content_type}
        if use_auth:
            headers.update(auth_headers)
        if idempotency_key is not None:
            headers["X-Idempotency-Key"] = idempotency_key
        return client.post("/ingesta", content=text.encode("utf-8"), headers=headers)
    return _ingesta


@pytest.fixture(autouse=True)
def _reset_polar_telemetry():
    """ADR-025: reset the process-global EWMA tracker around each test.

    `_variance_tracker` in traianus.app carries cross-ingestion continuity
    in production; in tests it must start (and end) clean so EWMA state
    never leaks between tests.
    """
    main._variance_tracker.reset()
    yield
    main._variance_tracker.reset()


@pytest.fixture(autouse=True)
def _hermetic_model(request, monkeypatch):
    """
    L1 Hermeticity: except for tests marked @pytest.mark.model (E2E with
    the cached real model), a deterministic fake encoder is injected to
    avoid loading MiniLM and any network access in unit tests.
    """
    if "model" in request.keywords:
        yield
        return
    fake = FakeSentenceTransformer()
    # Store originals for cleanup
    orig_main = main._provider
    orig_main_get = main.get_provider
    orig_bootstrap = bootstrap._provider
    orig_bootstrap_get = bootstrap.get_provider
    try:
        monkeypatch.setattr(main, "_provider", fake)
        monkeypatch.setattr(main, "get_provider", lambda: fake)
        monkeypatch.setattr(bootstrap, "_provider", fake)
        monkeypatch.setattr(bootstrap, "get_provider", lambda: fake)
        yield
    finally:
        # Restore originals to prevent state leakage between tests
        monkeypatch.undo()