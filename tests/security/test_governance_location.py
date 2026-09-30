"""The Zero-Trust gate lives in tools/governance/, outside the deterministic engine (AGENTS.md 3.1, 6.2).

Guards the move from the former engine subpackage: the gate imports from its new path, the former
package is gone, nothing in the code or the tests still names it, and the audit database is the
engine's, unchanged.
"""
from pathlib import Path

import pytest

from tools.governance import hook_gate, validator
from tools.governance.hook_gate import has_recent_execute_safe, is_governed_path
from tools.governance.schemas.proposals import (
    AgentMutationProposal,
    build_response_format,
)
from tools.governance.validator import validate_proposal
from traianus import storage

ROOT = Path(__file__).resolve().parents[2]
FORMER_DOTTED = "traianus." + "security"
FORMER_PATH = "traianus/" + "security"


def test_the_gate_is_importable_from_tools_governance():
    for name in (validate_proposal, has_recent_execute_safe, is_governed_path,
                 AgentMutationProposal, build_response_format):
        assert name is not None


def test_the_former_package_no_longer_exists():
    assert not (ROOT / "traianus" / "security").exists()
    with pytest.raises(ImportError):
        __import__(FORMER_DOTTED)


def test_no_module_or_test_names_the_former_location():
    sources = [
        path for tree in ("traianus", "tools", "tests") for path in (ROOT / tree).rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    named = [
        str(path.relative_to(ROOT)) for path in sources
        if any(former in path.read_text(encoding="utf-8") for former in (FORMER_DOTTED, FORMER_PATH))
    ]
    assert not named, f"still name the former location: {named}"


def test_the_audit_database_is_the_engines_and_unchanged():
    """B5: the gate copies the engine's database name and writes through traianus.storage."""
    assert hook_gate.DEFAULT_DB_NAME == "traianus.db"
    assert validator.storage is storage


def test_a_repointed_engine_database_is_honoured_by_both_halves(tmp_path, monkeypatch):
    active = tmp_path / "repointed.db"
    monkeypatch.setattr(storage, "DB_PATH", str(active))
    validator._persist_audit("case-x", "EXECUTE_SAFE", "DOC", "docs/x.md", "NONE")
    assert active.exists()
    assert hook_gate._db_path() == active
