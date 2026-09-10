"""PreToolUse enforcement gate (AGENTS.md SS5.2, tools/hooks/require_boundary_validation.py).

Covers: which paths are governed, and whether a recent boundary-validator
EXECUTE_SAFE for the exact target file is detected regardless of whether
validate_proposal was called with a relative or absolute Target_File."""
import json
import sqlite3

import pytest

import traianus.storage as storage
from traianus.security.hook_gate import REPO_ROOT, has_recent_execute_safe, is_governed_path
from traianus.security.validator import validate_proposal


def _doc_proposal(target_file: str) -> str:
    # Intent_Class DOC skips the grounding gate (validator.py:119), so any
    # placeholder quote is enough to isolate the recency/path-matching logic
    # under test here from grounding behaviour already covered elsewhere.
    return json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target_file,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
    })


@pytest.mark.parametrize("path", [
    "traianus/geometry/polar_projector.py",
    "tests/security/test_boundary_validator.py",
    "AGENTS.md",
    "docs/specifications/simplex_control_spec.md",
])
def test_is_governed_path_includes(path):
    assert is_governed_path(str(REPO_ROOT / path)) is True


@pytest.mark.parametrize("path", [
    "tools/hooks/require_boundary_validation.py",
    "tools/experiments/decompose_polar_latency.py",
    "docs/roadmap/NEXT_RESEARCH.md",
    ".claude/settings.json",
    ".opencode/skills/spec-first/SKILL.md",
])
def test_is_governed_path_excludes(path):
    assert is_governed_path(str(REPO_ROOT / path)) is False


def test_is_governed_path_rejects_outside_repo():
    assert is_governed_path("/tmp/not-in-repo/AGENTS.md") is False


def test_recent_execute_safe_detected(isolate_db):
    # target_file travels as validate_proposal's own out-of-band argument
    # (mirrors the MCP tool's `target_file` parameter) — that's what
    # _persist_audit logs to audit_log.target_file, independently of
    # whatever "Target_File" the JSON body itself carries.
    target = "docs/x.md"
    decision = validate_proposal(_doc_proposal(target), target)
    assert decision["final_decision"] == "EXECUTE_SAFE"

    assert has_recent_execute_safe(str(REPO_ROOT / target)) is True


def test_matches_absolute_target_against_relative_proposal(isolate_db):
    """validate_proposal was called with a relative target_file ('AGENTS.md',
    as an interactive caller naturally would); the hook receives an absolute
    tool_input.file_path from Claude Code. Both must resolve to the same
    identity, not compare as raw strings."""
    decision = validate_proposal(_doc_proposal("AGENTS.md"), "AGENTS.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"

    assert has_recent_execute_safe(str(REPO_ROOT / "AGENTS.md")) is True


def test_no_matching_row_is_not_recent(isolate_db):
    validate_proposal(_doc_proposal("docs/other.md"), "docs/other.md")
    assert has_recent_execute_safe(str(REPO_ROOT / "docs/unrelated.md")) is False


def test_non_execute_safe_decision_does_not_count(isolate_db):
    target = "docs/x.md"
    decision = validate_proposal(json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "BOUNDARY_VIOLATION",
    }), target)
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"

    assert has_recent_execute_safe(str(REPO_ROOT / target)) is False


def test_stale_execute_safe_outside_window(isolate_db):
    target = "docs/x.md"
    decision = validate_proposal(_doc_proposal(target), target)
    with sqlite3.connect(isolate_db) as conn:
        conn.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-3600 seconds') "
            "WHERE case_id = ?",
            (decision["case_id"],),
        )

    assert has_recent_execute_safe(str(REPO_ROOT / target), window_seconds=900) is False


def test_unreadable_db_raises_for_fail_closed_caller(monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", "/definitely/not/a/real/dir/x.db")
    with pytest.raises(Exception):
        has_recent_execute_safe(str(REPO_ROOT / "AGENTS.md"))
