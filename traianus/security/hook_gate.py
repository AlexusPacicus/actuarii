"""PreToolUse enforcement gate (AGENTS.md SS5.2, SS6.2): pure, testable
checks used by tools/hooks/require_boundary_validation.py to block Edit/Write
on governed paths unless boundary-validator already logged EXECUTE_SAFE for
that exact file recently.

Standard library only, deliberately: the harness spawns the hook with an
ambient PATH and cwd, so the interpreter running this may be a bare system
Python with none of the substrate's dependencies installed. An import error
here exits 1, which the harness reads as a broken hook rather than as a
denial -- the gate would fail OPEN. Hence no import of traianus.storage, and
hence the database name copied below instead of imported.

Reuses the audit trail traianus.security.validator._persist_audit already
writes to the audit_log table (traianus/storage/_storage.py) instead of
introducing a second receipt mechanism.
"""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Copy of traianus.storage.DB_PATH, not an import; see the module docstring.
# tests/security/test_hook_startup_surface.py keeps the copy honest.
DEFAULT_DB_NAME = "traianus.db"

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


def _db_path() -> Path:
    """Absolute path of the audit database.

    When the substrate is already imported in this process (tests, tools) its
    DB_PATH wins, so a repointed database is honoured -- the module is read if
    present, never imported. A relative path is anchored at the repository
    root: the harness picks the cwd, and the gate's verdict must not depend on
    that choice.
    """
    storage = sys.modules.get("traianus.storage")
    configured = getattr(storage, "DB_PATH", DEFAULT_DB_NAME)
    path = Path(configured)
    return path if path.is_absolute() else REPO_ROOT / path


def has_recent_execute_safe(file_path: str, window_seconds: int = 900) -> bool:
    """True if audit_log has an EXECUTE_SAFE row for `file_path` within the
    last `window_seconds`.

    The database is opened read-only: this gate reads receipts, it never
    writes one, and a missing database or a missing audit_log table raises
    rather than being created -- an audit trail the verifier conjures for
    itself is not an audit trail.

    target_file in audit_log is whatever string the caller passed to
    validate_proposal (relative, absolute, or otherwise) — each candidate
    is resolved against REPO_ROOT the same way `file_path` is, so a match
    is by resolved identity, not raw string equality. Any DB error (path
    doesn't exist, locked, corrupt) propagates: the caller treats an
    exception here as "not verified" (fail-closed).
    """
    resolved_target = Path(file_path).expanduser().resolve()
    with closing(sqlite3.connect(f"{_db_path().as_uri()}?mode=ro", uri=True)) as conn:
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
