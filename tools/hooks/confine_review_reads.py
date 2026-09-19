"""PreToolUse hook: confine Read, Grep and Glob to a review package (AGENTS 6.1).

While `.data/review_lock.json` names a package directory, every path those tools would reach
must resolve (symlinks followed) inside it; anything else is denied with exit 2. Without a lock
the hook is inert. The lock is written and cleared by tools/audit/build_review_package.py; at
most one agent executes at a time, so it applies to whoever reads while a blind review runs.

Standard library only: an import failure would exit 1, which the harness reads as a broken hook
rather than a denial; annotations are postponed so a 3.9 system interpreter can import it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCK_PATH = REPO_ROOT / ".data" / "review_lock.json"
GATED_TOOLS = {"Read", "Grep", "Glob"}
GLOB_CHARS = set("*?[{")


class ReviewLockError(ValueError):
    pass


def read_lock(lock_path: Path) -> Path | None:
    if not lock_path.exists():
        return None
    try:
        package = Path(json.loads(lock_path.read_text(encoding="utf-8"))["package"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ReviewLockError(f"unreadable review lock {lock_path}: {exc}") from exc
    if not package.is_absolute() or not package.is_dir():
        raise ReviewLockError(f"review lock names no package directory: {package}")
    return package.resolve()


def _static_prefix(pattern: str) -> str:
    parts = []
    for part in Path(pattern).parts:
        if GLOB_CHARS & set(part):
            break
        parts.append(part)
    return str(Path(*parts)) if parts else ""


def _has_parent_segment(pattern: str) -> bool:
    return ".." in Path(pattern).parts


def _require_str(tool_input: dict, key: str, required: bool) -> str | None:
    value = tool_input.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise ReviewLockError(f"malformed tool input: {key!r}")
    return value


def target_paths(tool_name: str, tool_input: dict, cwd: Path) -> list[Path]:
    if tool_name == "Read":
        return [cwd / _require_str(tool_input, "file_path", True)]
    base = cwd / (_require_str(tool_input, "path", False) or ".")
    targets = [base]
    for key in ("pattern", "glob") if tool_name == "Glob" else ("glob",):
        pattern = _require_str(tool_input, key, tool_name == "Glob" and key == "pattern")
        if pattern is None:
            continue
        if _has_parent_segment(pattern):
            raise ReviewLockError(f"parent-directory segment in {key!r}: {pattern}")
        prefix = _static_prefix(pattern)
        if prefix:
            targets.append(base / prefix)
    return targets


def _inside(path: Path, package: Path) -> bool:
    return path.resolve().is_relative_to(package)


def decide(payload: dict, lock_path: Path = LOCK_PATH) -> tuple[bool, str]:
    if not lock_path.exists():
        return True, ""
    try:
        package = read_lock(lock_path)
        if package is None:
            return True, ""
        tool_name = payload.get("tool_name")
        if tool_name not in GATED_TOOLS:
            return True, ""
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            raise ReviewLockError("malformed tool input")
        cwd = Path(payload.get("cwd") or REPO_ROOT)
        for target in target_paths(tool_name, tool_input, cwd):
            if not _inside(target, package):
                return False, f"{target} is outside the review package {package}"
    except ReviewLockError as exc:
        return False, str(exc)
    return True, ""


def main(stdin_text: str, lock_path: Path = LOCK_PATH) -> int:
    try:
        payload = json.loads(stdin_text)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        if not lock_path.exists():
            return 0
        sys.stderr.write("[confine_review_reads] fail-closed: malformed hook input.\n")
        return 2
    allowed, reason = decide(payload, lock_path)
    if not allowed:
        sys.stderr.write(
            f"[confine_review_reads] blind review in progress: {reason}. Read only the "
            "package; the executing agent clears the lock when the verdict is in.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.read()))
