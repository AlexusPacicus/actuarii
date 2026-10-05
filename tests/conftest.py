"""Root test configuration: the repository root on sys.path and the audit database isolation."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.boundary_validator import hook_gate  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_audit_db(tmp_path, monkeypatch):
    """
    The boundary validator's audit database per test under tmp_path: its
    location is a hook_gate attribute, so no test touches the real
    .data/boundary_validator_audit.db nor the engine database.
    """
    audit_db = tmp_path / "boundary_validator_audit.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", audit_db)
    return audit_db
