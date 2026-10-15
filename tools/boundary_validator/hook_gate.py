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
and Implementation_Block, nothing normalised. has_receipt, receipt_case and has_any_receipt
read it; has_recent_execute_safe keeps reading audit_log, for the tools that write something
the gate cannot compare.

What a governed write leaves is the gate's own record, the `writes` table of the same database
(WRITES_DDL): before the hook allows an Edit, MultiEdit or Write, record_write adds one row with the
file's repository-relative path, the tool, the SHA-256 of the file before (NULL when it did not exist)
and of what the write leaves, and the case_ids of the receipts that cover it.
tools/git/commit_record.py reads the rows back with recorded_writes, with the rationale of each
receipt taken from audit_log, and compares them with a commit. Every query opens the database
read-only; record_write opens it in mode rw, so it creates neither the database nor its directory,
and it creates the `writes` table in a database that has none.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from tools import project_config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_AUDIT_DB = REPO_ROOT / ".data" / "boundary_validator_audit.db"
AUDIT_DB_PATH: Path | str = DEFAULT_AUDIT_DB

WRITES_DDL = """
CREATE TABLE IF NOT EXISTS writes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    target_file TEXT NOT NULL,
    tool TEXT NOT NULL,
    before_sha256 TEXT,
    after_sha256 TEXT NOT NULL,
    receipts TEXT NOT NULL
)
"""


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


def _recent_receipts(file_path: str, window_seconds: int) -> list[tuple[str, str, str]]:
    """(case_id, grounding_sha256, block_sha256) of the receipts for `file_path` within the window, the most recent first."""
    resolved_target = Path(file_path).expanduser().resolve()
    with closing(sqlite3.connect(f"{_db_path().as_uri()}?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            "SELECT case_id, target_file, grounding_sha256, block_sha256 FROM receipts "
            "WHERE datetime(timestamp) >= datetime('now', ?) "
            "ORDER BY datetime(timestamp) DESC, rowid DESC",
            (f"-{window_seconds} seconds",),
        ).fetchall()
    return [
        (case_id, grounding, block) for case_id, raw_target, grounding, block in rows
        if _names(raw_target, resolved_target)
    ]


def receipt_case(file_path: str, block_sha256: str, grounding_sha256: str | None = None,
                 window_seconds: int = project_config.DEFAULT_WINDOW) -> str | None:
    """The case_id of the most recent receipt within the window that names `file_path` and carries `block_sha256`
    and, unless `grounding_sha256` is None, that grounding; None when there is none.

    Read-only, like has_receipt: a missing database or table raises.
    """
    for case_id, grounding, block in _recent_receipts(file_path, window_seconds):
        if block == block_sha256 and (grounding_sha256 is None or grounding == grounding_sha256):
            return case_id
    return None


def has_receipt(file_path: str, block_sha256: str, grounding_sha256: str | None = None,
                window_seconds: int = project_config.DEFAULT_WINDOW) -> bool:
    return receipt_case(file_path, block_sha256, grounding_sha256, window_seconds) is not None


def has_any_receipt(file_path: str, window_seconds: int = project_config.DEFAULT_WINDOW) -> bool:
    return bool(_recent_receipts(file_path, window_seconds))


def record_write(target_file: str, tool: str, before_sha256: str | None, after_sha256: str,
                 receipts: list[str]) -> None:
    """Adds to the `writes` table the write that the gate is about to allow.

    `target_file` is the repository-relative POSIX path as the gate spells it, `before_sha256` the SHA-256 of the
    file as it is (None when it does not exist), `after_sha256` the SHA-256 of what the write leaves and `receipts`
    the case_ids of the receipts that cover it. The database is opened in mode rw, so a missing database or
    directory is an error and never created; the table is created in the same transaction as the row. Any
    sqlite3.Error or OSError propagates: the caller then denies the write.
    """
    row = (target_file, tool, before_sha256, after_sha256, json.dumps(receipts))
    with closing(sqlite3.connect(f"{_db_path().as_uri()}?mode=rw", uri=True)) as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(WRITES_DDL)
            conn.execute(
                "INSERT INTO writes (target_file, tool, before_sha256, after_sha256, receipts) "
                "VALUES (?, ?, ?, ?, ?)",
                row,
            )


def recorded_writes(target_file: str) -> list[tuple[str | None, str, list[str | None]]]:
    """(before_sha256, after_sha256, rationales) of the writes recorded for `target_file`, in the order recorded.

    `target_file` is compared as the gate stored it, byte for byte. The rationales are those of the row's
    receipts, in their order with each case_id taken once, as audit_log holds them: None for a receipt that
    audit_log does not have or whose rationale is NULL. Read-only. A database without the `writes` table gives
    []; a missing database, a missing audit_log table or any other error raises.
    """
    with closing(sqlite3.connect(f"{_db_path().as_uri()}?mode=ro", uri=True)) as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'writes'").fetchone() is None:
            return []
        rows = conn.execute(
            "SELECT before_sha256, after_sha256, receipts FROM writes WHERE target_file = ? ORDER BY id",
            (target_file,),
        ).fetchall()
        known: dict[str, str | None] = {}
        written = []
        for before, after, receipts in rows:
            cases = list(dict.fromkeys(json.loads(receipts)))
            for case_id in cases:
                if case_id not in known:
                    found = conn.execute("SELECT rationale FROM audit_log WHERE case_id = ?", (case_id,)).fetchone()
                    known[case_id] = None if found is None else found[0]
            written.append((before, after, [known[case_id] for case_id in cases]))
    return written
