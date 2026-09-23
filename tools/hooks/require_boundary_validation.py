#!/usr/bin/env python3
"""Claude Code PreToolUse hook: enforce AGENTS.md SS5.2 ("Agents MUST NOT
assume direct host OS execution authority") for Edit/Write on governed
paths.

Reads the PreToolUse JSON payload from stdin ({"tool_name": ...,
"tool_input": {"file_path": ...}, ...}). Exits 0 (allow) unless the target
is a governed path with no recent boundary-validator EXECUTE_SAFE, in
which case it exits 2 (blocking) with an explanatory message on stderr.
Any failure to verify (bad DB, bad payload shape while a governed path is
still identifiable) fails closed.

The target is decided by what the filesystem says it is, not by how it is
spelled: `canonical` resolves it (symlinks, `..`) and re-spells it with the
names its directory entries store, found by identity, before the gate looks at
it. On a case-insensitive filesystem `TESTS/x.py` is therefore `tests/x.py`. A
path inside the repository that the filesystem cannot be asked about is denied.
A receipt is matched against that stored spelling, so validate_proposal must be
given it (the denial prints it).
"""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from traianus.security.hook_gate import has_recent_execute_safe, is_governed_path
except Exception as exc:  # fail-closed: a gate that cannot start must deny
    # An unhandled failure here exits 1, which the harness reads as a broken
    # hook and not as a denial: the edit would proceed ungated.
    sys.stderr.write(
        "[require_boundary_validation] fail-closed: the boundary gate could "
        f"not be imported ({exc}). Denying instead of leaving the edit "
        "ungated.\n"
    )
    sys.exit(2)

GATED_TOOLS = {"Edit", "Write"}


def _same(samefile: Callable[..., bool], first: str | Path, second: Path) -> bool:
    try:
        return samefile(first, second)
    except FileNotFoundError:
        return False


def canonical(
    target: str | Path,
    root: Path,
    samefile: Callable[..., bool] = os.path.samefile,
    scandir: Callable[..., Any] = os.scandir,
) -> Path | None:
    """`target` resolved, then re-spelled with the names the filesystem stores; None outside `root`.

    A case-insensitive filesystem lets `TESTS/x.py` name `tests/x.py`, so names are matched by
    identity, never by spelling: the ancestor that is the same file as `root` is found with
    `samefile`, and below it each name becomes the directory entry that is the same file as the
    spelled one. What does not exist yet (a new file) stays as spelled. An OSError while looking for
    the root only means "not that ancestor"; past the root it propagates, and so does one on the
    root itself, so an unreadable root cannot make every path read as outside. Both hooks under
    tools/hooks carry this function; a test compares the copies.
    """
    samefile(root, root)
    path = Path(target).resolve()
    for anchor in (path, *path.parents):
        try:
            if samefile(anchor, root):
                break
        except OSError:
            continue
    else:
        return None
    real, spelled = Path(root), anchor
    names = path.relative_to(anchor).parts
    for index, name in enumerate(names):
        spelled = spelled / name
        with scandir(real) as entries:
            found = sorted(
                entry.name for entry in entries
                if not entry.is_symlink() and _same(samefile, entry.path, spelled)
            )
        if not found:
            return real.joinpath(*names[index:])
        real = real / (name if name in found else found[0])
    return real


def main(
    samefile: Callable[..., bool] = os.path.samefile, scandir: Callable[..., Any] = os.scandir
) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: stdin was not valid "
            "JSON; cannot verify whether the target is a governed path.\n"
        )
        return 2  # R2/INV-2: unparseable input blocks, same as every other unverifiable case

    if payload.get("tool_name") not in GATED_TOOLS:
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0

    try:
        try:
            target = canonical(Path(file_path).expanduser(), REPO_ROOT, samefile, scandir)
        except (OSError, RuntimeError, ValueError) as exc:
            sys.stderr.write(
                "[require_boundary_validation] fail-closed: cannot tell whether "
                f"{file_path!r} is inside the repository ({exc}).\n"
            )
            return 2
        if target is None or not is_governed_path(str(target)):
            return 0
        if has_recent_execute_safe(str(target)):
            return 0
    except Exception as exc:  # fail-closed: an unverifiable audit trail blocks
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: could not verify "
            f"the boundary-validator audit trail ({exc}).\n"
        )
        return 2

    sys.stderr.write(
        f"[require_boundary_validation] {target} is a governed path "
        "(AGENTS.md SS5.1/SS5.2: traianus/, tests/, AGENTS.md, "
        "docs/specifications/) with no recent EXECUTE_SAFE in audit_log. "
        "Call mcp__boundary-validator__validate_proposal for this exact "
        "file first, then retry.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
