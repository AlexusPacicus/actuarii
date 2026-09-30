"""PreToolUse enforcement gate (AGENTS.md SS5.2, SS6.2): pure, testable
checks used by tools/hooks/require_boundary_validation.py to block Edit/Write
on governed paths unless boundary-validator already logged EXECUTE_SAFE for
that exact file recently.

Standard library only, deliberately: the harness spawns the hook with an
ambient PATH and cwd, so the interpreter running this may be a bare system
Python with none of the substrate's dependencies installed. An import error
here exits 1, which the harness reads as a broken hook rather than as a
denial -- the gate would fail OPEN. Hence no import of traianus.

The gate owns the location of the audit trail: AUDIT_DB_PATH, read at call
time, and tools.boundary_validator.validator._persist_audit writes the
audit_log table (its DDL lives there) to the path _db_path() returns, so the
writer and the reader cannot diverge. The location is a module attribute,
never an environment variable or a config file: the hook would trust a path
an agent can set. Tests repoint the attribute in process.
"""
import sqlite3
from contextlib import closing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_AUDIT_DB = REPO_ROOT / ".data" / "boundary_validator_audit.db"
AUDIT_DB_PATH: Path | str = DEFAULT_AUDIT_DB

GOVERNED_TOP_LEVEL = {"traianus", "tests"}
GOVERNED_SINGLE_FILES = {"AGENTS.md"}
GOVERNED_SUBTREES = {("docs", "specifications"), ("tools", "boundary_validator")}


def is_governed_path(file_path: str) -> bool:
    """True if `file_path` falls under a path governed by AGENTS.md SS5.

    Governed: traianus/**, tests/**, AGENTS.md, docs/specifications/**,
    tools/boundary_validator/**. Everything else (the rest of tools/, docs/roadmap/,
    .claude/, .opencode/, ...) is deliberately left ungoverned.
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

    A relative AUDIT_DB_PATH is anchored at the repository root: the harness
    picks the cwd, and the gate's verdict must not depend on that choice.
    """
    path = Path(AUDIT_DB_PATH)
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
