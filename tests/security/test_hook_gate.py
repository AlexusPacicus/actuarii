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


def test_audit_db_path_matches_validator_regardless_of_cwd(tmp_path, monkeypatch):
    """R1/INV-1 (REMEDIATION-01 Delta1): _persist_audit must resolve a relative
    DB_PATH against REPO_ROOT the same way hook_gate._db_path() does -- not
    against whichever directory the process happens to be running in."""
    from traianus.security import hook_gate

    relative_name = "test_audit_symmetry.db"
    monkeypatch.setattr(storage, "DB_PATH", relative_name)
    monkeypatch.chdir(tmp_path)

    expected = hook_gate.REPO_ROOT / relative_name
    try:
        decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
        assert decision["final_decision"] == "EXECUTE_SAFE"

        assert expected.exists(), (
            "_persist_audit wrote relative to cwd instead of REPO_ROOT, "
            f"diverging from hook_gate._db_path() == {expected}"
        )
        assert hook_gate._db_path() == expected
    finally:
        expected.unlink(missing_ok=True)
        (expected.parent / (expected.name + "-wal")).unlink(missing_ok=True)
        (expected.parent / (expected.name + "-shm")).unlink(missing_ok=True)


def test_malformed_stdin_json_blocks(monkeypatch):
    """R2/INV-2 (REMEDIATION-01 Delta1): malformed JSON on stdin must exit 2
    (block), not 0 (allow) -- the hook's fail-closed claim (AGENTS.md SS6.2)
    is total only if every unparseable input blocks too. Loaded as a plain
    module (not spawned) and driven through a replaced sys.stdin, so no host
    process primitive is needed to exercise main() end to end."""
    import io
    import sys

    hooks_dir = str(REPO_ROOT / "tools" / "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import require_boundary_validation as hook_script

    monkeypatch.setattr(sys, "stdin", io.StringIO("{not valid json"))
    assert hook_script.main() == 2


def test_persist_audit_closes_connection(isolate_db, monkeypatch):
    """R9/INV-10: _persist_audit must close its connection deterministically;
    `with conn` commits but leaves the handle to the garbage collector."""
    from traianus.security import validator

    opened = []
    real = sqlite3.connect

    def tracking(*args, **kwargs):
        conn = real(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(validator.sqlite3, "connect", tracking)
    validator._persist_audit("close-check", "EXECUTE_SAFE", "DOC", "docs/x.md", "NONE")
    assert opened
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
