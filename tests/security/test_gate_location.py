"""The Zero-Trust gate lives in tools/boundary_validator/, outside the deterministic engine (AGENTS.md 3.1, 6.2).

Guards the moves from the former locations: the gate imports from its current path, neither former
package exists, nothing in the code or the tests still names them, and the audit database is the
engine's, unchanged. traianus/governance/, the engine's consolidation gate, is another component and
stays allowed.
"""
from pathlib import Path

import pytest

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.hook_gate import has_recent_execute_safe, is_governed_path
from tools.boundary_validator.schemas.proposals import (
    AgentMutationProposal,
    build_response_format,
)
from tools.boundary_validator.validator import validate_proposal
from traianus import storage

ROOT = Path(__file__).resolve().parents[2]
FORMER_LOCATIONS = (
    ("traianus." + "security", "traianus/" + "security"),
    ("tools." + "governance", "tools/" + "governance"),
)


def test_the_gate_is_importable_from_tools_boundary_validator():
    for name in (validate_proposal, has_recent_execute_safe, is_governed_path,
                 AgentMutationProposal, build_response_format):
        assert name is not None


@pytest.mark.parametrize("dotted, path", FORMER_LOCATIONS)
def test_the_former_packages_no_longer_exist(dotted, path):
    assert not (ROOT / path).exists()
    with pytest.raises(ImportError):
        __import__(dotted)


def test_no_module_or_test_names_the_former_locations():
    sources = [
        path for tree in ("traianus", "tools", "tests") for path in (ROOT / tree).rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    named = [
        str(path.relative_to(ROOT)) for path in sources
        if any(former in path.read_text(encoding="utf-8") for names in FORMER_LOCATIONS for former in names)
    ]
    assert not named, f"still name a former location: {named}"


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
