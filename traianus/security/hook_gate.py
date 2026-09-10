"""PreToolUse enforcement gate (AGENTS.md SS5.2): pure, testable checks used
by tools/hooks/require_boundary_validation.py to block Edit/Write on
governed paths unless boundary-validator already logged EXECUTE_SAFE for
that exact file recently.

Reuses the audit trail traianus.security.validator._persist_audit already
writes to the audit_log table (traianus/storage/_storage.py) instead of
introducing a second receipt mechanism.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from traianus.storage import AUDIT_LOG_DDL, get_db_connection

GOVERNED_TOP_LEVEL = {"traianus", "tests"}
GOVERNED_SINGLE_FILES = {"AGENTS.md"}
GOVERNED_SUBTREES = {("docs", "specifications")}


def is_governed_path(file_path: str) -> bool:
    """True if `file_path` falls under a path governed by AGENTS.md SS5.

    Governed: traianus/**, tests/**, AGENTS.md, docs/specifications/**.
    Everything else (tools/, docs/roadmap/, .claude/, .opencode/, ...) is
    deliberately left ungoverned.
    """
    try:
        resolved = Path(file_path).expanduser().resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(REPO_ROOT):
        return False
    rel_parts = resolved.relative_to(REPO_ROOT).parts
    if not rel_parts:
        return False
    if rel_parts[0] in GOVERNED_SINGLE_FILES:
        return True
    if rel_parts[0] in GOVERNED_TOP_LEVEL:
        return True
    if rel_parts[:2] in GOVERNED_SUBTREES:
        return True
    return False


def has_recent_execute_safe(file_path: str, window_seconds: int = 900) -> bool:
    """True if audit_log has an EXECUTE_SAFE row for `file_path` within the
    last `window_seconds`.

    target_file in audit_log is whatever string the caller passed to
    validate_proposal (relative, absolute, or otherwise) — each candidate
    is resolved against REPO_ROOT the same way `file_path` is, so a match
    is by resolved identity, not raw string equality. Any DB error (path
    doesn't exist, locked, corrupt) propagates: the caller treats an
    exception here as "not verified" (fail-closed).
    """
    resolved_target = Path(file_path).expanduser().resolve()
    with get_db_connection() as conn:
        conn.execute(AUDIT_LOG_DDL)
        rows = conn.execute(
            "SELECT target_file FROM audit_log WHERE decision = 'EXECUTE_SAFE' "
            "AND datetime(timestamp) >= datetime('now', ?)",
            (f"-{window_seconds} seconds",),
        ).fetchall()
    for (raw_target,) in rows:
        if not raw_target:
            continue
        candidate = Path(raw_target)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
        try:
            if candidate.resolve() == resolved_target:
                return True
        except OSError:
            continue
    return False
