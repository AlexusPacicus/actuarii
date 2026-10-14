"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Config perimeter as parsed structure (SEC-M-13): both permission matrices --
`opencode.jsonc` (OpenCode) and `.claude/settings.json` (Claude Code) -- are
normalized to a {pattern: decision} mapping and asserted as semantics rather
than as text, and both MUST declare one and the same perimeter.

Complements `test_opencode_permissions.py`, which stays text-level on purpose:
rule ORDER is a textual property in OpenCode (last match wins) and cannot be
asserted over a parsed mapping.

Normative: the permission perimeter of both harnesses
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

# Primitives that MUST be denied in every matrix.
REQUIRED_DENY = {"rm *", "python3 -c *", "python3 -m *", "webfetch", "websearch"}

# Besides read-only git and the scripts under tools/, the ONLY Bash patterns that MAY be granted "allow":
# pytest and the closed list of read-only commands (the permission perimeter of the constitution).
READ_ONLY_COMMANDS = ("ls", "cat", "head", "tail", "wc", "grep", "df", "echo", "sed -n", "sort", "uniq", "diff")
READ_ONLY_ALLOW = (
    "pytest", "pytest *", "ls", "ls *", "cat *", "head *", "tail *", "wc *", "grep *", "df", "df *",
    "echo *", "sed -n *", "sort *", "uniq *", "diff *",
)

# The only other rule that MAY be granted "allow": validate_proposal of the MCP server boundary-validator, which
# writes only the audit trail. Claude Code names it mcp__<server>__<tool>; OpenCode joins server and tool with an
# underscore, and that is the name both matrices carry.
VALIDATOR_RULE = "boundary-validator_validate_proposal"
CLAUDE_VALIDATOR_ENTRY = "mcp__boundary-validator__validate_proposal"

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
    for tool, decision in permission.items():
        if tool != "bash":
            assert isinstance(decision, str), f"opencode.jsonc: permission {tool!r} must be one decision"
            matrix[tool] = decision
    return matrix


def _normalize_claude_entry(entry: str) -> str:
    """Map a Claude Code permission entry onto the OpenCode pattern space."""
    if entry.startswith("Bash(") and entry.endswith(")"):
        return entry[len("Bash("):-1]
    if entry == "Bash":
        return "*"  # bare tool name is the catch-all bash rule
    if entry.startswith("mcp__"):
        server, _, tool = entry[len("mcp__"):].partition("__")
        return f"{server}_{tool}"  # mcp__server__tool -> server_tool, the name OpenCode gives the tool
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
    """A python3 allow MUST target committed scripts under
    tools/ or traianus/."""
    name, rules = matrix
    for pattern, decision in rules.items():
        if decision != ALLOW or not pattern.startswith("python3 "):
            continue
        argument = pattern[len("python3 "):]
        assert argument.startswith(("tools/", "traianus/")), (
            f"{name}: python3 allow {argument!r} escapes tools/ and traianus/"
        )


def _unlisted_allows(rules: dict) -> list:
    """The allowed rules outside the closed list: a read-only git subcommand, a python3 script under tools/,
    pytest or a read-only command (READ_ONLY_ALLOW) and the validator's rule."""
    unlisted = []
    for pattern, decision in rules.items():
        if decision != ALLOW:
            continue
        if pattern.startswith("git "):
            listed = pattern[len("git "):].replace("*", "").strip() in APPROVED_GIT_ALLOW
        elif pattern.startswith("python3 "):
            listed = pattern[len("python3 "):].startswith("tools/")
        else:
            listed = pattern in READ_ONLY_ALLOW or pattern == VALIDATOR_RULE
        if not listed:
            unlisted.append(pattern)
    return unlisted


def test_security_SEC_M_13_allow_list_is_closed(matrix):
    """Every allowed rule MUST be on the closed list of the permission perimeter; anything else asks."""
    name, rules = matrix
    unlisted = _unlisted_allows(rules)
    assert unlisted == [], f"{name}: allow rules outside the closed list: {unlisted}"


CLOSED_LIST = {
    pattern: ALLOW
    for pattern in (*READ_ONLY_ALLOW, VALIDATOR_RULE, "git status", "git ls-files *", "python3 tools/audit/*")
}


@pytest.mark.parametrize(
    "rules, unlisted",
    [
        pytest.param(CLOSED_LIST, [], id="the-closed-list"),
        pytest.param({"cat *": ASK, "find *": DENY}, [], id="only-allows-count"),
        pytest.param({"sed *": ALLOW}, ["sed *"], id="sed-without-n"),
        pytest.param({"find *": ALLOW}, ["find *"], id="find"),
        pytest.param({"git *": ALLOW}, ["git *"], id="git-wildcard"),
        pytest.param({"git push *": ALLOW}, ["git push *"], id="git-push"),
        pytest.param({"python3 scripts/*": ALLOW}, ["python3 scripts/*"], id="python3-outside-tools"),
        pytest.param({"other-server_other-tool": ALLOW}, ["other-server_other-tool"], id="another-mcp-tool"),
        pytest.param({"edit": ALLOW}, ["edit"], id="a-file-tool"),
        pytest.param({"*": ALLOW}, ["*"], id="catch-all"),
    ],
)
def test_security_SEC_M_13_closed_list_names_what_falls_outside(rules, unlisted):
    assert _unlisted_allows(rules) == unlisted


def test_security_SEC_M_13_claude_allows_the_read_only_commands_and_the_validator():
    """.claude/settings.json MUST allow, after its git and python3 entries, pytest, the read-only commands and
    the validator's tool."""
    allow = json.loads(CLAUDE.read_text(encoding="utf-8"))["permissions"]["allow"]
    expected = [f"Bash({pattern})" for pattern in READ_ONLY_ALLOW] + [CLAUDE_VALIDATOR_ENTRY]
    assert allow[-len(expected):] == expected, (
        f".claude/settings.json: the last {len(expected)} allow entries are {allow[-len(expected):]}"
    )


def test_security_SEC_M_13_opencode_allows_the_read_only_commands_and_the_validator():
    """opencode.jsonc MUST allow the same bash patterns and the validator's tool under the name OpenCode gives it."""
    permission = json.loads(_strip_line_comments(OPENCODE.read_text(encoding="utf-8")))["permission"]
    missing = [pattern for pattern in READ_ONLY_ALLOW if permission["bash"].get(pattern) != ALLOW]
    assert missing == [], f"opencode.jsonc: bash patterns not allowed: {missing}"
    assert permission.get(VALIDATOR_RULE) == ALLOW, f"opencode.jsonc: {VALIDATOR_RULE!r} is not allowed"


AGENTS_MD = ROOT / "AGENTS.md"


def test_security_SEC_M_13_agents_clause_7_1_names_what_the_perimeter_allows():
    """Clause 7.1 of AGENTS.md MUST name pytest, each read-only command and the validator's tool."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    start = text.index("7.1 `.claude/settings.json`")
    clause = text[start:text.index("\n\n", start)]
    names = ["pytest", *READ_ONLY_COMMANDS, "validate_proposal"]
    missing = [name for name in names if f"`{name}`" not in clause]
    assert missing == [], f"clause 7.1 of AGENTS.md does not name: {missing}"


def test_security_SEC_M_13_perimeter_parity_between_harnesses():
    """Both matrices MUST declare the same perimeter. A rule
    granted in one harness and missing from the other is drift."""
    opencode = _opencode_matrix()
    claude = _claude_matrix()
    opencode_only = {p: d for p, d in opencode.items() if claude.get(p) != d}
    claude_only = {p: d for p, d in claude.items() if opencode.get(p) != d}
    assert not opencode_only and not claude_only, (
        f"perimeter drift -- only in opencode.jsonc: {opencode_only}; "
        f"only in .claude/settings.json: {claude_only}"
    )


def test_every_python_allow_names_a_path_that_exists(matrix):
    name, rules = matrix
    missing = [
        pattern for pattern, decision in rules.items()
        if decision == ALLOW and pattern.startswith("python3 ")
        and not (ROOT / pattern[len("python3 "):].split("*")[0]).exists()
    ]
    assert missing == [], f"{name}: python3 allows for paths that do not exist"


CLAUDE_MD = ROOT / "CLAUDE.md"


def test_opencode_loads_the_instructions_that_claude_md_imports():
    imported = re.findall(r"^@(\S+)$", CLAUDE_MD.read_text(encoding="utf-8"), re.MULTILINE)
    opencode = json.loads(_strip_line_comments(OPENCODE.read_text(encoding="utf-8")))
    assert imported
    assert opencode["instructions"] == imported
    assert [path for path in imported if not (ROOT / path).is_file()] == []


def test_line_comment_stripper_preserves_urls_inside_strings():
    """The stripper MUST NOT read '//' inside a string as a comment, or the
    '$schema' URL would be truncated and the parse would fail."""
    text = '{"$schema": "https://opencode.ai/config.json", // note\n "a": 1}'
    assert json.loads(_strip_line_comments(text)) == {
        "$schema": "https://opencode.ai/config.json",
        "a": 1,
    }


MCP_CONFIG = ROOT / ".mcp.json"
GATE_SERVER = "tools/boundary_validator/validator.py"


def _launched_server_script():
    """Script each harness launches as the boundary-validator MCP server."""
    mcp = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    opencode = json.loads(_strip_line_comments(OPENCODE.read_text(encoding="utf-8")))
    return {
        ".mcp.json": mcp["mcpServers"]["boundary-validator"]["args"][-1],
        "opencode.jsonc": opencode["mcp"]["boundary-validator"]["command"][-1],
    }


def test_security_boundary_validator_server_launches_from_tools_boundary_validator():
    """Both harnesses MUST launch the gate from its current path."""
    assert _launched_server_script() == {".mcp.json": GATE_SERVER, "opencode.jsonc": GATE_SERVER}
    assert (ROOT / GATE_SERVER).is_file()


def test_every_declared_mcp_server_launches_a_script_that_exists():
    mcp = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    opencode = json.loads(_strip_line_comments(OPENCODE.read_text(encoding="utf-8")))
    launched = {
        (".mcp.json", name): server["args"][-1] for name, server in mcp["mcpServers"].items()
    } | {
        ("opencode.jsonc", name): server["command"][-1] for name, server in opencode["mcp"].items()
    }
    assert [key for key, script in launched.items() if not (ROOT / script).is_file()] == []


def test_security_permission_matrices_allow_the_gate_where_it_lives(matrix):
    name, rules = matrix
    assert rules.get(f"python3 {GATE_SERVER}") == ALLOW, f"{name}: the gate script is not allowed"


@pytest.mark.parametrize("config", [MCP_CONFIG, OPENCODE, CLAUDE], ids=lambda p: p.name)
def test_security_no_config_names_the_former_gate_location(config):
    text = config.read_text(encoding="utf-8")
    assert "traianus/" + "security" not in text
    assert "tools/" + "governance" not in text
