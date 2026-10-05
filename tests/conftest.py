"""Root test configuration: the repository root on sys.path and the audit database isolation."""
import json
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


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """
    Points project_config at a configuration under tmp_path; call the result with a dict or raw text to write
    it. Until it is called there is no file, so the gate runs on the built-in minimum.
    """
    from tools import project_config

    path = tmp_path / ".actuarii.json"
    monkeypatch.setattr(project_config, "CONFIG_PATH", path)

    def write(content):
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    return write
