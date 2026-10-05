"""The project configuration: `.actuarii.json` at the repository root.

It tells the write gate (tools/boundary_validator/hook_gate.py) which paths it governs and how long a
boundary-validator receipt counts:

    {"schema": "actuarii-config/1", "governed_paths": [<patterns>], "receipt_window_seconds": <1..86400>}

A pattern is a path relative to the root: `*` stays inside one segment, `**` crosses segments, the rest is
literal. The file is read strictly: every deviation is a ConfigError naming its cause, never a default. Without
the file the gate governs a built-in minimum and its verdicts say so. The file itself is always governed.

Standard library only, JSON and not TOML, and importable by a Python 3.9 interpreter: the gate imports this
module, and an import error exits 1, which the harness reads as a broken hook and not as a denial, so the gate
would fail open. The location is a module attribute, never an environment variable: the gate would trust a path
an agent can set. Tests repoint it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_NAME = ".actuarii.json"
CONFIG_PATH = ROOT / CONFIG_NAME
SCHEMA = "actuarii-config/1"
KEYS = ("schema", "governed_paths", "receipt_window_seconds")
DEFAULT_WINDOW = 900
MAX_WINDOW = 86400
BUILT_IN_PATHS = (CONFIG_NAME, "AGENTS.md", "CLAUDE.md")
BUILT_IN_SOURCE = "built-in minimum (no .actuarii.json)"
OWN_RULE = "always governed: the project configuration"
WILDCARDS = re.compile(r"(\*\*/|\*\*|\*)")
GLOB_REGEX = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*"}
UNSUPPORTED = re.compile(r"[?\[\]{}]|\*{3,}")


class ConfigError(ValueError):
    """The configuration cannot be trusted; the message names the file and the cause."""


@dataclass(frozen=True)
class ProjectConfig:
    governed_paths: tuple[str, ...]
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


def load() -> ProjectConfig:
    """The configuration at CONFIG_PATH, validated; the built-in minimum when the file does not exist."""
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ProjectConfig(BUILT_IN_PATHS, DEFAULT_WINDOW, BUILT_IN_SOURCE)
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
    window = data["receipt_window_seconds"]
    if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= MAX_WINDOW:
        raise _error(f"receipt_window_seconds must be an integer from 1 to {MAX_WINDOW}, got {window!r}")
    return ProjectConfig(tuple(paths), window, CONFIG_NAME)


def path_matches(pattern: str, rel: str) -> bool:
    """`*` stays inside one path segment, `**` crosses segments; everything else is literal."""
    regex = "".join(GLOB_REGEX.get(part, re.escape(part)) for part in WILDCARDS.split(pattern))
    return re.fullmatch(regex, rel) is not None


def governance(rel: str) -> Governance | None:
    """The rule that governs `rel` (a path relative to the root, with `/`), or None when nothing does.

    The configuration file is governed whatever it says and whatever state it is in: when it is invalid it
    stays subject to a receipt with the default window, so the rules can always be repaired under a receipt.
    Any other path raises ConfigError while the configuration is invalid.
    """
    try:
        config = load()
    except ConfigError:
        if rel == CONFIG_NAME:
            return Governance(OWN_RULE, CONFIG_NAME, DEFAULT_WINDOW)
        raise
    if rel == CONFIG_NAME:
        return Governance(OWN_RULE, config.source, config.receipt_window_seconds)
    for pattern in config.governed_paths:
        if path_matches(pattern, rel):
            return Governance(f'governed_paths entry "{pattern}"', config.source, config.receipt_window_seconds)
    return None
