"""PreToolUse enforcement gate: pure, testable checks used by
tools/hooks/require_boundary_validation.py to block Edit/Write on governed
paths unless boundary-validator already logged EXECUTE_SAFE for that exact
file recently.

Which paths are governed, and for how long a receipt counts, is not decided
here: it comes from the project configuration (.actuarii.json, read by
tools/project_config.py).

Standard library only, deliberately: the harness spawns the hook with an
ambient PATH and cwd, so the interpreter running this may be a bare system
Python with none of the substrate's dependencies installed. An import error
here exits 1, which the harness reads as a broken hook rather than as a
denial -- the gate would fail OPEN. Hence the only module imported besides
the standard library is tools.project_config, itself standard library only,
and annotations are postponed so a Python 3.9 interpreter can import this.

The gate owns the location of the audit trail: AUDIT_DB_PATH, read at call
time, and tools.boundary_validator.validator._persist_audit writes the
audit_log table (its DDL lives there) to the path _db_path() returns, so the
writer and the reader cannot diverge. The location is a module attribute,
never an environment variable or a config file: the hook would trust a path
an agent can set. Tests repoint the attribute in process.

A receipt is a row of the `receipts` table of that database (case_id, timestamp,
target_file, grounding_sha256, block_sha256), written by the validator only with
EXECUTE_SAFE: the SHA-256 of the UTF-8 bytes of the proposal's Topological_Grounding
and Implementation_Block, nothing normalised. has_receipt and has_any_receipt read it;
has_recent_execute_safe keeps reading audit_log, for the tools that write something the
gate cannot compare.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from tools import project_config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_AUDIT_DB = REPO_ROOT / ".data" / "boundary_validator_audit.db"
AUDIT_DB_PATH: Path | str = DEFAULT_AUDIT_DB


def governing_rule(file_path: str) -> project_config.Governance | None:
    """The project-configuration rule that governs `file_path`, or None.

    None for a path outside the repository root and for one no rule covers.
    Raises project_config.ConfigError while the configuration is invalid,
    except for the configuration file itself, which is always governed.
    """
    try:
        resolved = Path(file_path).expanduser().resolve()
    except OSError:
        return None
    if not resolved.is_relative_to(REPO_ROOT):
        return None
    rel = resolved.relative_to(REPO_ROOT).as_posix()
    if rel == ".":
        return None
    return project_config.governance(rel)


def _db_path() -> Path:
    """Absolute path of the audit database.

    A relative AUDIT_DB_PATH is anchored at the repository root: the harness
    picks the cwd, and the gate's verdict must not depend on that choice.
    """
    path = Path(AUDIT_DB_PATH)
    return path if path.is_absolute() else REPO_ROOT / path


def audit_trail_exists() -> bool:
    """True if something exists at the audit database path, usable or not.

    It only tells a trail that has not been started (the validator creates the
    database on its first call) from one that cannot be read; it creates nothing
    and the receipt queries still raise on whatever they cannot use.
    """
    return os.path.lexists(_db_path())


def has_recent_execute_safe(file_path: str, window_seconds: int = project_config.DEFAULT_WINDOW) -> bool:
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
    return any(_names(raw_target, resolved_target) for (raw_target,) in rows)


def _names(raw_target: str | None, resolved_target: Path) -> bool:
    if not raw_target:
        return False
    candidate = Path(raw_target)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        return candidate.resolve() == resolved_target
    except OSError:
        return False


def _recent_receipts(file_path: str, window_seconds: int) -> list[tuple[str, str]]:
    resolved_target = Path(file_path).expanduser().resolve()
    with closing(sqlite3.connect(f"{_db_path().as_uri()}?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            "SELECT target_file, grounding_sha256, block_sha256 FROM receipts "
            "WHERE datetime(timestamp) >= datetime('now', ?)",
            (f"-{window_seconds} seconds",),
        ).fetchall()
    return [(grounding, block) for raw_target, grounding, block in rows if _names(raw_target, resolved_target)]


def has_receipt(file_path: str, block_sha256: str, grounding_sha256: str | None = None,
                window_seconds: int = project_config.DEFAULT_WINDOW) -> bool:
    return any(
        block == block_sha256 and (grounding_sha256 is None or grounding == grounding_sha256)
        for grounding, block in _recent_receipts(file_path, window_seconds)
    )


def has_any_receipt(file_path: str, window_seconds: int = project_config.DEFAULT_WINDOW) -> bool:
    return bool(_recent_receipts(file_path, window_seconds))
