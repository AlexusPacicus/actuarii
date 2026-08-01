"""
Root test harness configuration (Phase 0: Foundations).

Shared fixtures that ELIMINATE the DDL and isolation duplication that
existed in the 34 pre-Phase 0 tests (two byte-for-byte copies of the same schema):
- `operator_token_env` (autouse): TRAIANUS_TOKEN for protected routes (H3).
- `isolate_db` (autouse): ephemeral SQLite DB per test, single DDL via
  `helpers/db_factory.create_test_db`, monkeypatch of `main.DB_PATH`.
- `client`: TestClient of FastAPI over the real app.
- `auth_headers`: valid operator header.
- `_hermetic_model` (autouse): injects a fake encoder (L1) into all
  tests except those marked `@pytest.mark.model` (E2E with real model).
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT, TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import traianus.app as main  # noqa: E402
import traianus.bootstrap as bootstrap  # noqa: E402
from helpers.db_factory import create_test_db  # noqa: E402
from helpers.fake_encoder import FakeSentenceTransformer  # noqa: E402

AUTH_TOKEN = "test-operator-token"


@pytest.fixture(autouse=True)
def operator_token_env(monkeypatch):
    """Sets TRAIANUS_TOKEN for protected routes (H3). Fail-closed:
    without this env, require_token rejects with 401."""
    monkeypatch.setenv("TRAIANUS_TOKEN", AUTH_TOKEN)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """
    Ephemeral SQLite DB per test with the canonical schema (single DDL in
    helpers/db_factory.py). Replaces the two duplicated fixtures
    pre-Phase 0 (test_control_plane.isolate_test_database and
    test_append_only_log.isolate_append_only_db).
    """
    test_db_path = str(tmp_path / "test_traianus.db")
    monkeypatch.setattr(main, "DB_PATH", test_db_path)
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
    monkeypatch.setattr(main, "model", fake)
    monkeypatch.setattr(bootstrap, "model", fake)
    yield