"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Config perimeter (SEC-M-13): the opencode.jsonc bash permission matrix must
not grant a 'git *' wildcard allow; only the explicit read/inspection git
subcommands (status, diff, log, show, rev-parse, grep, blame, ls-files, add)
may be allowed, and the deny primitives (webfetch, websearch, rm *) persist.
Normative: docs/exploring/legacy_docs/development/tests/SPEC-security.md
Coverage: SEC-M-13"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "opencode.jsonc"

# The ONLY git subcommands that MAY be granted "allow" (read/inspection).
APPROVED_ALLOW = {
    "status",
    "diff",
    "log",
    "show",
    "rev-parse",
    "grep",
    "blame",
    "ls-files",
    "add",
}

_GIT_ALLOW_RE = re.compile(r'"git\s+([a-z0-9-]+(?:\s+\*)?)"\s*:\s*"allow"')
_GIT_WILDCARD_ALLOW_RE = re.compile(r'"git\s+\*"\s*:\s*"allow"')


def _config_text() -> str:
    return CONFIG.read_text(encoding="utf-8")


def test_security_SEC_M_13_no_git_wildcard_allow_entry():
    """SEC-M-13: the opencode.jsonc bash matrix MUST NOT grant a 'git *'
    wildcard allow (no bare subcommand wildcard may be an allow entry)."""
    text = _config_text()
    assert '"git *": "allow"' not in text
    assert not _GIT_WILDCARD_ALLOW_RE.search(text)


def test_security_SEC_M_13_git_allow_entries_only_read_inspection():
    """SEC-M-13: every '"git X": "allow"' entry MUST be one of the explicit
    read/inspection subcommands (APPROVED_ALLOW); no mutating/remote git
    subcommand (commit, push, merge, reset, ...) may be allowed."""
    text = _config_text()
    entries = _GIT_ALLOW_RE.findall(text)
    assert entries, "opencode.jsonc must declare explicit git allow entries"
    for entry in entries:
        subcommand = entry.replace("*", "").strip()
        assert subcommand in APPROVED_ALLOW, (
            f"git {entry!r} is not an approved read-only allow; "
            f"allowed: {sorted(APPROVED_ALLOW)}"
        )


def test_security_SEC_M_13_deny_primitives_persist():
    """SEC-M-13 (perimeter): the deny primitives MUST persist — webfetch and
    websearch are denied and 'rm *' remains a deny entry."""
    text = _config_text()
    assert re.search(r'"rm\s+\*"\s*:\s*"deny"', text), "'rm *' must remain deny"
    assert re.search(r'"webfetch"\s*:\s*"deny"', text), "webfetch must remain deny"
    assert re.search(r'"websearch"\s*:\s*"deny"', text), "websearch must remain deny"


def test_security_SEC_M_13_broad_catchall_precedes_narrow_rules():
    """SEC-M-13 (ordering): opencode evaluates the LAST matching rule, so the
    broad catch-all '*' must be declared FIRST and the specific git rules
    AFTER it. A trailing '*' would shadow every allow/deny entry."""
    text = _config_text()
    star_index = text.index('"*": "ask"')
    rm_index = text.index('"rm *": "deny"')
    first_git_allow = text.index('"git status": "allow"')
    assert star_index < rm_index < first_git_allow, (
        "bash matrix must be broad-first: '*' ask, then 'rm *' deny, "
        "then the narrow git allow rules"
    )
