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
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from traianus.security.hook_gate import has_recent_execute_safe, is_governed_path

GATED_TOOLS = {"Edit", "Write"}


def main() -> int:
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
        if not is_governed_path(file_path):
            return 0
        if has_recent_execute_safe(file_path):
            return 0
    except Exception as exc:  # fail-closed: an unverifiable audit trail blocks
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: could not verify "
            f"the boundary-validator audit trail ({exc}).\n"
        )
        return 2

    sys.stderr.write(
        f"[require_boundary_validation] {file_path} is a governed path "
        "(AGENTS.md SS5.1/SS5.2: traianus/, tests/, AGENTS.md, "
        "docs/specifications/) with no recent EXECUTE_SAFE in audit_log. "
        "Call mcp__boundary-validator__validate_proposal for this exact "
        "file first, then retry.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
