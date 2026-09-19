"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Config perimeter as parsed structure (SEC-M-13): both permission matrices --
`opencode.jsonc` (OpenCode) and `.claude/settings.json` (Claude Code) -- are
normalized to a {pattern: decision} mapping and asserted as semantics rather
than as text, and both MUST declare one and the same perimeter.

Complements `test_opencode_permissions.py`, which stays text-level on purpose:
rule ORDER is a textual property in OpenCode (last match wins) and cannot be
asserted over a parsed mapping.

Normative: AGENTS.md 2.5, 6.2
Coverage: SEC-M-13"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OPENCODE = ROOT / "opencode.jsonc"
CLAUDE = ROOT / ".claude" / "settings.json"

ALLOW = "allow"
ASK = "ask"
DENY = "deny"

# The ONLY git subcommands that MAY be granted "allow" (read/inspection).
APPROVED_GIT_ALLOW = {
    "status", "diff", "log", "show", "rev-parse", "grep", "blame", "ls-files",
}

# Primitives that MUST be denied in every matrix (AGENTS.md 2.5, 6.2).
REQUIRED_DENY = {"rm *", "python3 -c *", "python3 -m *", "webfetch", "websearch"}

# Alternation order matters: a string literal is consumed whole, so a `//`
# inside one (e.g. "https://opencode.ai/config.json") is never a comment.
_STRING_OR_COMMENT = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*')


def _strip_line_comments(text: str) -> str:
    return _STRING_OR_COMMENT.sub(
        lambda m: "" if m.group().startswith("//") else m.group(), text
    )


def _opencode_matrix() -> dict:
    config = json.loads(_strip_line_comments(OPENCODE.read_text(encoding="utf-8")))
    permission = config["permission"]
    matrix = dict(permission["bash"])
    for tool in ("webfetch", "websearch"):
        matrix[tool] = permission[tool]
    return matrix


def _normalize_claude_entry(entry: str) -> str:
    """Map a Claude Code permission entry onto the OpenCode pattern space."""
    if entry.startswith("Bash(") and entry.endswith(")"):
        return entry[len("Bash("):-1]
    if entry == "Bash":
        return "*"  # bare tool name is the catch-all bash rule
    return entry.lower()  # WebFetch -> webfetch, WebSearch -> websearch


def _claude_matrix() -> dict:
    permissions = json.loads(CLAUDE.read_text(encoding="utf-8"))["permissions"]
    matrix = {}
    # Claude Code resolves deny > ask > allow, so for a repeated pattern the
    # strictest decision must be the one that survives normalization.
    for decision in (ALLOW, ASK, DENY):
        for entry in permissions.get(decision, []):
            matrix[_normalize_claude_entry(entry)] = decision
    return matrix


MATRICES = {"opencode.jsonc": _opencode_matrix, ".claude/settings.json": _claude_matrix}


@pytest.fixture(params=sorted(MATRICES))
def matrix(request):
    return request.param, MATRICES[request.param]()


def test_security_SEC_M_13_bash_default_is_ask(matrix):
    """The catch-all bash rule MUST be 'ask' in every matrix."""
    name, rules = matrix
    assert rules.get("*") == ASK, f"{name}: the catch-all bash rule must be 'ask'"


def test_security_SEC_M_13_required_denies_persist(matrix):
    """rm, inline python3 and the network tools MUST stay denied."""
    name, rules = matrix
    for pattern in sorted(REQUIRED_DENY):
        assert rules.get(pattern) == DENY, f"{name}: {pattern!r} must be denied"


def test_security_SEC_M_13_no_git_wildcard_allow(matrix):
    """A bare 'git *' allow would grant every mutating subcommand at once."""
    name, rules = matrix
    assert rules.get("git *") != ALLOW, f"{name}: 'git *' must never be allowed"


def test_security_SEC_M_13_git_allows_are_read_only(matrix):
    """Every granted git rule MUST be a read/inspection subcommand."""
    name, rules = matrix
    for pattern, decision in rules.items():
        if decision != ALLOW or not pattern.startswith("git "):
            continue
        subcommand = pattern[len("git "):].replace("*", "").strip()
        assert subcommand in APPROVED_GIT_ALLOW, (
            f"{name}: 'git {subcommand}' is not an approved read-only allow; "
            f"allowed: {sorted(APPROVED_GIT_ALLOW)}"
        )


def test_security_SEC_M_13_python_allows_stay_inside_committed_trees(matrix):
    """AGENTS.md 2.5: a python3 allow MUST target committed scripts under
    tools/ or traianus/."""
    name, rules = matrix
    for pattern, decision in rules.items():
        if decision != ALLOW or not pattern.startswith("python3 "):
            continue
        argument = pattern[len("python3 "):]
        assert argument.startswith(("tools/", "traianus/")), (
            f"{name}: python3 allow {argument!r} escapes tools/ and traianus/"
        )


def test_security_SEC_M_13_perimeter_parity_between_harnesses():
    """AGENTS.md 6.2: both matrices MUST declare the same perimeter. A rule
    granted in one harness and missing from the other is drift."""
    opencode = _opencode_matrix()
    claude = _claude_matrix()
    opencode_only = {p: d for p, d in opencode.items() if claude.get(p) != d}
    claude_only = {p: d for p, d in claude.items() if opencode.get(p) != d}
    assert not opencode_only and not claude_only, (
        f"perimeter drift -- only in opencode.jsonc: {opencode_only}; "
        f"only in .claude/settings.json: {claude_only}"
    )


def test_line_comment_stripper_preserves_urls_inside_strings():
    """The stripper MUST NOT read '//' inside a string as a comment, or the
    '$schema' URL would be truncated and the parse would fail."""
    text = '{"$schema": "https://opencode.ai/config.json", // note\n "a": 1}'
    assert json.loads(_strip_line_comments(text)) == {
        "$schema": "https://opencode.ai/config.json",
        "a": 1,
    }
