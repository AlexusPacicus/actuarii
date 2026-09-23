"""PreToolUse hook: the bit-level contracts are a precondition of the work on the vector path.

Edit and Write on a path registered in tools/hooks/contract_registry.json are denied (exit 2)
unless every contract section the matching rules require was served by tools/audit/context_pack.py
within `window_seconds`, from the contract file as it is now. The receipt is the `served` line
context_pack appends to .data/context_pack.log (path, kind, value, ts, file_sha256). A denial names
the missing sections and prints the context_pack command that serves them.

A target is decided by what the filesystem says it is, not by how it is spelled: the path is resolved
(symlinks, `..`) and then re-spelled by `canonical` with the names its directory entries store, found
by identity. On a case-insensitive filesystem `SRC/VEC.PY` is therefore the registered `src/vec.py`.

Fails closed: a registry that cannot be read or has the wrong shape denies every Edit/Write inside
the root, except an edit of the registry itself; for a registered target so do an unreadable log and
an unreadable contract file; so does a path inside the root that the filesystem cannot be asked
about. A missing log is an empty one: nothing was served.

Declared limits: the receipt proves that context_pack served the sections, not that the agent read
them nor that the code conforms (conformance is what tests are for). The log is a plain file, so a
line written through Bash forges a receipt; writes issued through Bash are not gated. The receipt
names neither agent nor session. tools/hooks/**, the registry included, is not itself gated. A
missing file has no identity: a case variant of a registry that no longer exists is not recognised
as the registry, and stays denied until the exact spelling is used.

Standard library only: an import failure would exit 1, which the harness reads as a broken hook
rather than a denial; annotations are postponed so a 3.9 system interpreter can import it.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = REPO_ROOT / ".data" / "context_pack.log"
REGISTRY_PATH = Path(__file__).resolve().parent / "contract_registry.json"
GATED_TOOLS = {"Edit", "Write"}
STAMP = "%Y-%m-%dT%H:%M:%SZ"
REQUIREMENT_KEYS = ("path", "kind", "value")
JSON_ERRORS = (ValueError, RecursionError)
WILDCARDS = re.compile(r"(\*\*/|\*\*|\*)")
GLOB_REGEX = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*"}
FAIL_CLOSED = "[require_contract_context] fail-closed:"


class RegistryError(ValueError):
    pass


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


def path_matches(pattern: str, rel: str) -> bool:
    """`*` stays inside one path segment, `**` crosses segments; everything else is literal."""
    regex = "".join(GLOB_REGEX.get(part, re.escape(part)) for part in WILDCARDS.split(pattern))
    return re.fullmatch(regex, rel) is not None


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _rule_ok(rule: object) -> bool:
    if not isinstance(rule, dict) or not _text(rule.get("name")):
        return False
    paths, requires = rule.get("paths"), rule.get("requires")
    if not (isinstance(paths, list) and paths and isinstance(requires, list) and requires):
        return False
    return all(_text(path) for path in paths) and all(
        isinstance(item, dict) and all(_text(item.get(key)) for key in REQUIREMENT_KEYS)
        for item in requires
    )


def load_registry(path: Path) -> dict:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, *JSON_ERRORS) as exc:
        raise RegistryError(f"cannot read the registry {path}: {exc}") from exc
    window = registry.get("window_seconds") if isinstance(registry, dict) else None
    rules = registry.get("rules") if isinstance(registry, dict) else None
    if (
        not isinstance(window, int) or isinstance(window, bool) or window < 1
        or not isinstance(rules, list) or not all(_rule_ok(rule) for rule in rules)
    ):
        raise RegistryError(
            f"the registry {path} has the wrong shape: window_seconds (positive integer) and "
            "rules [name, paths, requires [path, kind, value]]"
        )
    return registry


def matching_rules(registry: dict, rel: str) -> list[dict]:
    return [
        rule for rule in registry["rules"]
        if any(path_matches(pattern, rel) for pattern in rule["paths"])
    ]


def _requirements(rules: list[dict]) -> list[tuple[str, ...]]:
    found: list[tuple[str, ...]] = []
    for rule in rules:
        for item in rule["requires"]:
            requirement = tuple(item[key] for key in REQUIREMENT_KEYS)
            if requirement not in found:
                found.append(requirement)
    return found


def _fresh(stamp: str, now: float, window: int) -> bool:
    try:
        age = now - calendar.timegm(time.strptime(stamp, STAMP))
    except ValueError:
        return False
    return 0 <= age <= window


def _served(
    log_path: Path, digests: dict[str, str], now: float, window: int
) -> set[tuple[str, ...]]:
    try:
        raw = log_path.read_bytes()
    except FileNotFoundError:
        return set()
    served: set[tuple[str, ...]] = set()
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except JSON_ERRORS:
            continue
        if not isinstance(entry, dict) or entry.get("status") != "served":
            continue
        requirement = tuple(entry.get(key) for key in REQUIREMENT_KEYS)
        stamp = entry.get("ts")
        if (
            all(isinstance(part, str) for part in requirement) and isinstance(stamp, str)
            and digests.get(requirement[0]) == entry.get("file_sha256")
            and _fresh(stamp, now, window)
        ):
            served.add(requirement)
    return served


def _denial(target: str, rules: list[dict], missing: list[tuple[str, ...]], window: int) -> str:
    grouped: dict[str, list[dict[str, str]]] = {}
    for path, kind, value in missing:
        grouped.setdefault(path, []).append({kind: value})
    spec = {
        "task": f"contract context for {target}",
        "sources": [{"path": path, "select": select} for path, select in grouped.items()],
    }
    lines = [
        (
            f"[require_contract_context] {target} falls under "
            f"{', '.join(r['name'] for r in rules)}: its contracts must be served by context_pack "
            f"(within {window} s, from the file as it is now) before it is edited. Missing:"
        ),
        *(f"  {path} [{kind}={value}]" for path, kind, value in missing),
        "Serve them, then retry:",
        "python3 tools/audit/context_pack.py <<'EOF'",
        json.dumps(spec),
        "EOF",
    ]
    return "\n".join(lines)


def decide(
    payload: dict, root: Path, log_path: Path, registry_path: Path, now: float,
    samefile: Callable[..., bool] = os.path.samefile, scandir: Callable[..., Any] = os.scandir,
) -> str | None:
    """None allows the edit; a string is the reason it is denied."""
    if payload.get("tool_name") not in GATED_TOOLS:
        return None
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else None
    if file_path == "":
        return None
    if not isinstance(file_path, str):
        return f"{FAIL_CLOSED} malformed tool input; cannot tell what is being edited."
    try:
        base = root.resolve()
        target = canonical(base / Path(file_path).expanduser(), base, samefile, scandir)
        registry_target = canonical(registry_path, base, samefile, scandir)
    except (OSError, RuntimeError, ValueError) as exc:
        return f"{FAIL_CLOSED} cannot resolve {file_path!r} ({exc})."
    if target is None:
        return None
    try:
        registry = load_registry(registry_path)
    except RegistryError as exc:
        if target == registry_target:
            return None
        return (
            f"{FAIL_CLOSED} {exc}. Every Edit/Write inside the repository is denied until "
            f"{registry_path.name} is repaired; that file stays editable."
        )
    rel = target.relative_to(base).as_posix()
    rules = matching_rules(registry, rel)
    if not rules:
        return None
    required = _requirements(rules)
    digests: dict[str, str] = {}
    for contract in dict.fromkeys(item[0] for item in required):
        try:
            digests[contract] = hashlib.sha256((base / contract).read_bytes()).hexdigest()
        except OSError as exc:
            return f"{FAIL_CLOSED} cannot read the contract file {contract} ({exc}); {rel} is unverifiable."
    window = registry["window_seconds"]
    try:
        served = _served(log_path, digests, now, window)
    except OSError as exc:
        return f"{FAIL_CLOSED} cannot read the context_pack log {log_path} ({exc}); {rel} is unverifiable."
    missing = [item for item in required if item not in served]
    return _denial(rel, rules, missing, window) if missing else None


def main(
    stdin_text: str,
    root: Path = REPO_ROOT,
    log_path: Path = LOG_PATH,
    registry_path: Path = REGISTRY_PATH,
    now: float | None = None,
    samefile: Callable[..., bool] = os.path.samefile,
    scandir: Callable[..., Any] = os.scandir,
) -> int:
    try:
        payload = json.loads(stdin_text)
    except JSON_ERRORS:
        payload = None
    if not isinstance(payload, dict):
        sys.stderr.write(f"{FAIL_CLOSED} stdin was not a JSON object; cannot tell what is being edited.\n")
        return 2
    reason = decide(
        payload, root, log_path, registry_path, time.time() if now is None else now, samefile, scandir)
    if reason is None:
        return 0
    sys.stderr.write(reason + "\n")
    return 2


if __name__ == "__main__":
    try:
        text = sys.stdin.read()
    except (OSError, ValueError):
        text = ""  # unreadable input is malformed input: main denies it
    sys.exit(main(text))
