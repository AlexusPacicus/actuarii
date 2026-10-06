"""ConfigChange hook: a change to the project settings, the local settings or a skill is not applied to the
running session.

Claude Code applies a change to a settings file to the session in progress, and a `"disableAllHooks": true` in
`.claude/settings.local.json` would switch off every other hook of the kit. A ConfigChange hook that exits 2
stops the change from being applied to the session; the file still changes on disk, and the next session reads
it. A change to the user or policy settings is applied: the kit does not own those files.

It fails closed: a payload that is not a JSON object, or whose `source` is missing or unknown, blocks the change.
Standard library only, importable by a Python 3.9 interpreter, and it imports nothing of the repository, so an
import error cannot turn it into a hook that exits 1, which the harness reads as a failed hook and not as a
denial.
"""
from __future__ import annotations

import json
import sys

PREFIX = "[block_config_changes]"
BLOCKED_SOURCES = ("project_settings", "local_settings", "skills")
APPLIED_SOURCES = ("user_settings", "policy_settings")
UNNAMED = "(the payload names no file)"


def decide(text: str) -> tuple[int, str]:
    try:
        payload = json.loads(text)
    except ValueError as exc:
        return 2, f"{PREFIX} blocked: the payload is not JSON ({exc})."
    if not isinstance(payload, dict):
        return 2, f"{PREFIX} blocked: the payload is not a JSON object."
    source = payload.get("source")
    if source in APPLIED_SOURCES:
        return 0, ""
    if source not in BLOCKED_SOURCES:
        return 2, f"{PREFIX} blocked: the payload has no known source ({source!r})."
    file_path = payload.get("file_path")
    named = file_path if isinstance(file_path, str) and file_path else UNNAMED
    return 2, (
        f"{PREFIX} {named} ({source}) changed during the session: the change is not applied to this session. "
        "If it stays on disk, it applies when the next session opens."
    )


def main() -> int:
    try:
        text = sys.stdin.read()
    except (OSError, ValueError) as exc:
        code, message = 2, f"{PREFIX} blocked: the payload could not be read ({exc})."
    else:
        code, message = decide(text)
    if message:
        sys.stderr.write(message + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
