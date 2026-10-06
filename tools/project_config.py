"""The project configuration: `.actuarii.json` at the repository root.

It tells the write gate (tools/boundary_validator/hook_gate.py) which paths it governs and how long a
boundary-validator receipt counts, the Python gate (tools/bin/python3) where Python may run, the
contract-context hook (tools/hooks/require_contract_context.py) where its registry lives, and the blind review
builder (tools/audit/build_review_package.py) what a review reads and what it never sees:

    {"schema": "actuarii-config/1", "governed_paths": [<patterns>], "python_script_dirs": [<directories>],
     "contract_registry": <path or null>, "review": <object or null>, "receipt_window_seconds": <1..86400>}

A pattern is a path relative to the root: `*` stays inside one segment, `**` crosses segments, the rest is
literal. A script directory is `.` (the whole root) or a plain path relative to the root, without wildcards; the
list may be empty. The contract registry is null (no registry: no path requires contract context) or a plain path
relative to the root, which the write gate governs whether or not governed_paths lists it. The review is null (no
blind review is configured) or an object with exactly these keys: `procedure` (a file), `base_docs` (a list of
files, possibly empty), `records` (a directory) and `denied` (a list, possibly empty, of prefixes that may end in
`/`); all are plain paths relative to the root, without duplicates. The file is read strictly: every deviation is a
ConfigError naming its cause, never a default. Without the file the gate governs a built-in minimum, scripts may
run from the whole root, there is no contract registry and no blind review, and the verdicts say so.
The file itself is always governed.

Run as `project_config.py --python-script-dirs` it prints the effective script directories, one per line, and
exits 0; with an invalid configuration it prints the error on stderr and exits 1; any other argv exits 2.

Standard library only, JSON and not TOML, and importable by a Python 3.9 interpreter: the gate imports this
module, and an import error exits 1, which the harness reads as a broken hook and not as a denial, so the gate
would fail open. The location is a module attribute, never an environment variable: the gate would trust a path
an agent can set. Tests repoint it.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_NAME = ".actuarii.json"
CONFIG_PATH = ROOT / CONFIG_NAME
SCHEMA = "actuarii-config/1"
KEYS = ("schema", "governed_paths", "python_script_dirs", "contract_registry", "review", "receipt_window_seconds")
REVIEW_KEYS = ("procedure", "base_docs", "records", "denied")
DEFAULT_WINDOW = 900
MAX_WINDOW = 86400
KIT_DIR = Path(__file__).resolve().parent.relative_to(ROOT).as_posix()
BUILT_IN_PATHS = (CONFIG_NAME, "AGENTS.md", "CLAUDE.md", ".claude/**", ".mcp.json", f"{KIT_DIR}/**")
BUILT_IN_SCRIPT_DIRS = (".",)
BUILT_IN_REGISTRY = None
BUILT_IN_REVIEW = None
BUILT_IN_SOURCE = "built-in minimum (no .actuarii.json)"
OWN_RULE = "always governed: the project configuration"
REGISTRY_RULE = "always governed: the contract registry"
WILDCARDS = re.compile(r"(\*\*/|\*\*|\*)")
GLOB_REGEX = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*"}
UNSUPPORTED = re.compile(r"[?\[\]{}]|\*{3,}")
DIR_WILDCARDS = re.compile(r"[*?\[\]{}]")
USAGE = "usage: project_config.py --python-script-dirs"


class ConfigError(ValueError):
    """The configuration cannot be trusted; the message names the file and the cause."""


@dataclass(frozen=True)
class ReviewConfig:
    """What a blind review reads (procedure, base documents, the directory of records) and what it never sees."""

    procedure: str
    base_docs: tuple[str, ...]
    records: str
    denied: tuple[str, ...]


@dataclass(frozen=True)
class ProjectConfig:
    governed_paths: tuple[str, ...]
    python_script_dirs: tuple[str, ...]
    contract_registry: str | None
    review: ReviewConfig | None
    receipt_window_seconds: int
    source: str


@dataclass(frozen=True)
class Governance:
    """Why a path is governed: the rule, where the rule comes from, and the receipt window in seconds."""

    rule: str
    source: str
    window_seconds: int


def _error(message: str) -> ConfigError:
    return ConfigError(f"{CONFIG_NAME}: {message}")


def _object(pairs: list) -> dict:
    keys = [key for key, _ in pairs]
    for key in keys:
        if keys.count(key) > 1:
            raise _error(f"duplicate key {key!r}")
    return dict(pairs)


def _constant(name: str) -> None:
    raise _error(f"the constant {name} is not allowed")


def _check_pattern(pattern: str) -> None:
    if pattern.startswith("/"):
        raise _error(f"governed_paths entry {pattern!r}: absolute paths are not allowed")
    if ".." in pattern:
        raise _error(f"governed_paths entry {pattern!r}: '..' is not allowed")
    if "\\" in pattern:
        raise _error(f"governed_paths entry {pattern!r}: a backslash is not allowed")
    if UNSUPPORTED.search(pattern):
        raise _error(f"governed_paths entry {pattern!r}: wildcards other than * and ** are not allowed")


def _check_plain_path(entry: str, where: str) -> None:
    if entry.startswith("/"):
        raise _error(f"{where}: absolute paths are not allowed")
    if ".." in entry:
        raise _error(f"{where}: '..' is not allowed")
    if "\\" in entry:
        raise _error(f"{where}: a backslash is not allowed")
    if any(ord(char) < 32 or ord(char) == 127 for char in entry):
        raise _error(f"{where}: control characters are not allowed")
    if DIR_WILDCARDS.search(entry):
        raise _error(f"{where}: wildcards are not allowed")
    if entry.endswith("/"):
        raise _error(f"{where}: a trailing slash is not allowed")
    if any(segment in ("", ".") for segment in entry.split("/")):
        raise _error(f"{where}: empty or '.' path segments are not allowed")


def _check_dir(entry: str) -> None:
    if entry != ".":
        _check_plain_path(entry, f"python_script_dirs entry {entry!r}")


def _check_registry(registry: object) -> None:
    if registry is None:
        return
    if not isinstance(registry, str) or not registry:
        raise _error("contract_registry must be null or a non-empty string")
    _check_plain_path(registry, f"contract_registry {registry!r}")


def _review_entry(entry: object, where: str, prefix: bool = False) -> str:
    """A plain path of the review; a denied prefix (`prefix`) may also end in one `/`."""
    if not isinstance(entry, str) or not entry:
        raise _error(f"{where} must be a non-empty string")
    _check_plain_path(entry[:-1] if prefix and entry.endswith("/") else entry, f"{where} {entry!r}")
    return entry


def _review_list(value: object, name: str, prefix: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _error(f"review.{name} must be a list of non-empty strings")
    entries = tuple(_review_entry(entry, f"review.{name} entry", prefix) for entry in value)
    if len(set(entries)) != len(entries):
        raise _error(f"review.{name} has duplicate entries")
    return entries


def _check_review(review: object) -> ReviewConfig | None:
    if review is None:
        return None
    if not isinstance(review, dict):
        raise _error("review must be null or an object")
    unknown = sorted(set(review) - set(REVIEW_KEYS))
    if unknown:
        raise _error(f"review has unknown keys {unknown}")
    missing = [key for key in REVIEW_KEYS if key not in review]
    if missing:
        raise _error(f"review is missing keys {missing}")
    return ReviewConfig(
        _review_entry(review["procedure"], "review.procedure"),
        _review_list(review["base_docs"], "base_docs"),
        _review_entry(review["records"], "review.records"),
        _review_list(review["denied"], "denied", prefix=True),
    )


def load() -> ProjectConfig:
    """The configuration at CONFIG_PATH, validated; the built-in minimum when the file does not exist."""
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ProjectConfig(
            BUILT_IN_PATHS, BUILT_IN_SCRIPT_DIRS, BUILT_IN_REGISTRY, BUILT_IN_REVIEW, DEFAULT_WINDOW, BUILT_IN_SOURCE)
    except UnicodeDecodeError as exc:
        raise _error(f"not valid UTF-8 ({exc})") from exc
    except OSError as exc:
        raise _error(f"cannot read {CONFIG_PATH} ({exc})") from exc
    try:
        data = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise _error(f"not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise _error("must be a JSON object")
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise _error(f"unknown keys {unknown}")
    missing = [key for key in KEYS if key not in data]
    if missing:
        raise _error(f"missing keys {missing}")
    if data["schema"] != SCHEMA:
        raise _error(f"schema must be {SCHEMA!r}, got {data['schema']!r}")
    paths = data["governed_paths"]
    if not isinstance(paths, list) or not paths or not all(isinstance(path, str) and path for path in paths):
        raise _error("governed_paths must be a non-empty list of non-empty strings")
    if len(set(paths)) != len(paths):
        raise _error("governed_paths has duplicate entries")
    for pattern in paths:
        _check_pattern(pattern)
    dirs = data["python_script_dirs"]
    if not isinstance(dirs, list) or not all(isinstance(entry, str) and entry for entry in dirs):
        raise _error("python_script_dirs must be a list of non-empty strings")
    if len(set(dirs)) != len(dirs):
        raise _error("python_script_dirs has duplicate entries")
    for entry in dirs:
        _check_dir(entry)
    registry = data["contract_registry"]
    _check_registry(registry)
    review = _check_review(data["review"])
    window = data["receipt_window_seconds"]
    if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= MAX_WINDOW:
        raise _error(f"receipt_window_seconds must be an integer from 1 to {MAX_WINDOW}, got {window!r}")
    return ProjectConfig(tuple(paths), tuple(dirs), registry, review, window, CONFIG_NAME)


def path_matches(pattern: str, rel: str) -> bool:
    """`*` stays inside one path segment, `**` crosses segments; everything else is literal."""
    regex = "".join(GLOB_REGEX.get(part, re.escape(part)) for part in WILDCARDS.split(pattern))
    return re.fullmatch(regex, rel) is not None


def governance(rel: str) -> Governance | None:
    """The rule that governs `rel` (a path relative to the root, with `/`), or None when nothing does.

    The configuration file is governed whatever it says and whatever state it is in: when it is invalid it
    stays subject to a receipt with the default window, so the rules can always be repaired under a receipt.
    The contract registry it names is governed whether or not governed_paths lists it, so that dropping a
    requirement always leaves a receipt. Any other path raises ConfigError while the configuration is invalid.
    """
    try:
        config = load()
    except ConfigError:
        if rel == CONFIG_NAME:
            return Governance(OWN_RULE, CONFIG_NAME, DEFAULT_WINDOW)
        raise
    if rel == CONFIG_NAME:
        return Governance(OWN_RULE, config.source, config.receipt_window_seconds)
    if rel == config.contract_registry:
        return Governance(REGISTRY_RULE, config.source, config.receipt_window_seconds)
    for pattern in config.governed_paths:
        if path_matches(pattern, rel):
            return Governance(f'governed_paths entry "{pattern}"', config.source, config.receipt_window_seconds)
    return None


def main(argv: list[str]) -> int:
    """The script directories for the Python gate, one per line; the error on stderr when the file is invalid."""
    if argv != ["--python-script-dirs"]:
        sys.stderr.write(f"{USAGE}\n")
        return 2
    try:
        config = load()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write("".join(f"{entry}\n" for entry in config.python_script_dirs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
