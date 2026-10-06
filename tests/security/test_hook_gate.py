"""PreToolUse enforcement gate (tools/hooks/require_boundary_validation.py).

Covers: which paths the project configuration governs, the receipt window it sets, the rule each denial
names, and whether a recent boundary-validator EXECUTE_SAFE for the exact target file is detected regardless
of whether validate_proposal was called with a relative or absolute Target_File."""
import io
import json
import re
import sqlite3
import sys
from contextlib import closing

import pytest

from tools.boundary_validator import hook_gate
from tools.boundary_validator.hook_gate import REPO_ROOT, governing_rule, has_recent_execute_safe
from tools.boundary_validator.validator import validate_proposal
from tools.hooks import require_boundary_validation


def _doc_proposal(target_file: str) -> str:
    # Intent_Class DOC skips the grounding gate (validator.py:119), so any
    # placeholder quote is enough to isolate the recency/path-matching logic
    # under test here from grounding behaviour already covered elsewhere.
    return json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target_file,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "NONE",
    })


CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**", "docs/specs/*.md", "NOTES.md"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 60,
}
REGISTRY_RULE = "always governed: the contract registry"
WITH_REGISTRY = {**CONFIG, "contract_registry": "contracts/registry.json"}


@pytest.mark.parametrize("path", [
    "src/a.py",
    "src/deep/b.py",
    "docs/specs/x.md",
    "NOTES.md",
    ".actuarii.json",
])
def test_governing_rule_includes(config_file, path):
    config_file(CONFIG)
    assert governing_rule(str(REPO_ROOT / path)) is not None


@pytest.mark.parametrize("path", [
    "tests/x.py",
    "AGENTS.md",
    "srcs/a.py",
    "docs/specs/deep/x.md",
    "docs/x.md",
    "tools/hooks/require_boundary_validation.py",
    ".claude/settings.json",
])
def test_governing_rule_excludes(config_file, path):
    config_file(CONFIG)
    assert governing_rule(str(REPO_ROOT / path)) is None


def test_governing_rule_rejects_outside_repo(config_file):
    config_file(CONFIG)
    assert governing_rule("/tmp/not-in-repo/NOTES.md") is None


def test_governing_rule_carries_the_configured_window(config_file):
    config_file(CONFIG)
    assert governing_rule(str(REPO_ROOT / "src" / "a.py")).window_seconds == 60


def test_recent_execute_safe_detected():
    # target_file travels as validate_proposal's own out-of-band argument
    # (mirrors the MCP tool's `target_file` parameter) — that's what
    # _persist_audit logs to audit_log.target_file, independently of
    # whatever "Target_File" the JSON body itself carries.
    target = "docs/x.md"
    decision = validate_proposal(_doc_proposal(target), target)
    assert decision["final_decision"] == "EXECUTE_SAFE"

    assert has_recent_execute_safe(str(REPO_ROOT / target)) is True


def test_matches_absolute_target_against_relative_proposal():
    """validate_proposal was called with a relative target_file ('AGENTS.md',
    as an interactive caller naturally would); the hook receives an absolute
    tool_input.file_path from Claude Code. Both must resolve to the same
    identity, not compare as raw strings."""
    decision = validate_proposal(_doc_proposal("AGENTS.md"), "AGENTS.md")
    assert decision["final_decision"] == "EXECUTE_SAFE"

    assert has_recent_execute_safe(str(REPO_ROOT / "AGENTS.md")) is True


def test_no_matching_row_is_not_recent():
    validate_proposal(_doc_proposal("docs/other.md"), "docs/other.md")
    assert has_recent_execute_safe(str(REPO_ROOT / "docs/unrelated.md")) is False


def test_non_execute_safe_decision_does_not_count():
    target = "docs/x.md"
    decision = validate_proposal(json.dumps({
        "Intent_Class": "DOC",
        "Target_File": target,
        "Topological_Grounding": "q",
        "Implementation_Block": "b",
        "Safety_Abort": "BOUNDARY_VIOLATION",
    }), target)
    assert decision["final_decision"] == "BLOCKED_BY_SAFETY_GATE"

    assert has_recent_execute_safe(str(REPO_ROOT / target)) is False


def test_stale_execute_safe_outside_window(isolate_audit_db):
    target = "docs/x.md"
    decision = validate_proposal(_doc_proposal(target), target)
    with sqlite3.connect(isolate_audit_db) as conn:
        conn.execute(
            "UPDATE audit_log SET timestamp = datetime('now', '-3600 seconds') "
            "WHERE case_id = ?",
            (decision["case_id"],),
        )

    assert has_recent_execute_safe(str(REPO_ROOT / target), window_seconds=900) is False


def test_unreadable_db_raises_for_fail_closed_caller(monkeypatch):
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", "/definitely/not/a/real/dir/x.db")
    with pytest.raises(Exception):
        has_recent_execute_safe(str(REPO_ROOT / "AGENTS.md"))


def test_audit_db_path_matches_validator_regardless_of_cwd(tmp_path, monkeypatch):
    """R1/INV-1 (REMEDIATION-01 Delta1): _persist_audit must resolve a relative
    AUDIT_DB_PATH against REPO_ROOT the same way hook_gate._db_path() does --
    not against whichever directory the process happens to be running in."""
    relative_name = "test_audit_symmetry.db"
    monkeypatch.setattr(hook_gate, "AUDIT_DB_PATH", relative_name)
    monkeypatch.chdir(tmp_path)

    expected = hook_gate.REPO_ROOT / relative_name
    try:
        decision = validate_proposal(_doc_proposal("docs/x.md"), "docs/x.md")
        assert decision["final_decision"] == "EXECUTE_SAFE"

        assert expected.exists(), (
            "_persist_audit wrote relative to cwd instead of REPO_ROOT, "
            f"diverging from hook_gate._db_path() == {expected}"
        )
        assert hook_gate._db_path() == expected
    finally:
        expected.unlink(missing_ok=True)
        (expected.parent / (expected.name + "-wal")).unlink(missing_ok=True)
        (expected.parent / (expected.name + "-shm")).unlink(missing_ok=True)


def test_malformed_stdin_json_blocks(monkeypatch):
    """R2/INV-2 (REMEDIATION-01 Delta1): malformed JSON on stdin must exit 2
    (block), not 0 (allow) -- the hook's fail-closed claim
    is total only if every unparseable input blocks too. Loaded as a plain
    module (not spawned) and driven through a replaced sys.stdin, so no host
    process primitive is needed to exercise main() end to end."""
    hooks_dir = str(REPO_ROOT / "tools" / "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import require_boundary_validation as hook_script

    monkeypatch.setattr(sys, "stdin", io.StringIO("{not valid json"))
    assert hook_script.main() == 2


def test_persist_audit_closes_connection(monkeypatch):
    """R9/INV-10: _persist_audit must close its connection deterministically;
    `with conn` commits but leaves the handle to the garbage collector."""
    from tools.boundary_validator import validator

    opened = []
    real = sqlite3.connect

    def tracking(*args, **kwargs):
        conn = real(*args, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(validator.sqlite3, "connect", tracking)
    validator._persist_audit("close-check", "EXECUTE_SAFE", "DOC", "docs/x.md", "NONE")
    assert opened
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


# the hook decides with the project configuration

OWN_RULE = "always governed: the project configuration"
BUILT_IN = "built-in minimum (no .actuarii.json)"
FOREIGN = re.compile(r"AGENTS|SS\d|(?i:traianus)")


def run_hook(monkeypatch, path, tool="Edit"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(path)}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return require_boundary_validation.main()


def grant(target):
    assert validate_proposal(_doc_proposal(target), target)["final_decision"] == "EXECUTE_SAFE"


def age(audit_db, target, seconds):
    with closing(sqlite3.connect(audit_db)) as conn, conn:
        conn.execute(
            "UPDATE audit_log SET timestamp = datetime('now', ?) WHERE target_file = ?",
            (f"-{seconds} seconds", target),
        )


@pytest.fixture
def trail():
    """The audit trail exists and holds a receipt for another file."""
    grant("docs/decoy.md")


# T3: the paths and the window come from the configuration

def test_a_path_the_configuration_governs_is_denied_without_a_receipt(monkeypatch, config_file, trail):
    config_file(CONFIG)
    assert run_hook(monkeypatch, REPO_ROOT / "src" / "a.py") == 2


def test_a_path_the_configuration_governs_is_allowed_with_a_recent_receipt(monkeypatch, config_file, trail):
    config_file(CONFIG)
    grant("src/a.py")
    assert run_hook(monkeypatch, REPO_ROOT / "src" / "a.py") == 0


@pytest.mark.parametrize("path", ["tests/x.py", "AGENTS.md"])
def test_a_path_the_configuration_does_not_govern_is_allowed_without_a_receipt(
        monkeypatch, config_file, trail, path):
    config_file(CONFIG)
    assert run_hook(monkeypatch, REPO_ROOT / path) == 0


def test_a_receipt_older_than_the_configured_window_does_not_count(
        monkeypatch, config_file, trail, isolate_audit_db):
    config_file(CONFIG)
    grant("src/a.py")
    age(isolate_audit_db, "src/a.py", 120)
    assert run_hook(monkeypatch, REPO_ROOT / "src" / "a.py") == 2


def test_a_receipt_inside_the_configured_window_counts(monkeypatch, config_file, trail, isolate_audit_db):
    config_file(CONFIG)
    grant("src/a.py")
    age(isolate_audit_db, "src/a.py", 30)
    assert run_hook(monkeypatch, REPO_ROOT / "src" / "a.py") == 0


def test_the_window_is_the_configured_one_and_not_a_fixed_900(monkeypatch, config_file, trail, isolate_audit_db):
    config_file({**CONFIG, "receipt_window_seconds": 3600})
    grant("src/a.py")
    age(isolate_audit_db, "src/a.py", 1000)
    assert run_hook(monkeypatch, REPO_ROOT / "src" / "a.py") == 0


def test_without_a_file_the_built_in_minimum_governs_and_names_itself(monkeypatch, capsys, config_file, trail):
    assert run_hook(monkeypatch, REPO_ROOT / "CLAUDE.md") == 2
    assert BUILT_IN in capsys.readouterr().err
    assert run_hook(monkeypatch, REPO_ROOT / "tests" / "x.py") == 0


@pytest.mark.parametrize("path", [".claude/settings.local.json", ".mcp.json", "tools/audit/x.py"])
def test_without_a_file_the_built_in_minimum_governs_the_wiring_and_the_kit(monkeypatch, capsys, config_file, trail, path):
    assert run_hook(monkeypatch, REPO_ROOT / path) == 2
    assert BUILT_IN in capsys.readouterr().err
    assert run_hook(monkeypatch, REPO_ROOT / "docs" / "x.md") == 0


# T3b: the configured contract registry is always governed

@pytest.mark.parametrize("governed", [["src/**"], ["src/**", "contracts/**"], ["contracts/registry.json"]])
def test_the_configured_registry_is_denied_without_a_receipt_whether_or_not_it_is_listed(
        monkeypatch, capsys, config_file, trail, governed):
    config_file({**WITH_REGISTRY, "governed_paths": governed})
    assert run_hook(monkeypatch, REPO_ROOT / "contracts" / "registry.json") == 2
    err = capsys.readouterr().err
    assert REGISTRY_RULE in err
    assert "source: .actuarii.json" in err
    assert "window: 60 s" in err


def test_the_configured_registry_is_allowed_with_a_recent_receipt(monkeypatch, config_file, trail):
    config_file(WITH_REGISTRY)
    grant("contracts/registry.json")
    assert run_hook(monkeypatch, REPO_ROOT / "contracts" / "registry.json") == 0


def test_without_a_registry_in_the_configuration_nothing_makes_that_path_governed(
        monkeypatch, config_file, trail):
    config_file(CONFIG)
    assert run_hook(monkeypatch, REPO_ROOT / "contracts" / "registry.json") == 0


def test_the_registry_receipt_follows_the_configured_window(monkeypatch, config_file, trail, isolate_audit_db):
    config_file(WITH_REGISTRY)
    grant("contracts/registry.json")
    age(isolate_audit_db, "contracts/registry.json", 120)
    assert run_hook(monkeypatch, REPO_ROOT / "contracts" / "registry.json") == 2


# T4: an invalid configuration never opens the gate

@pytest.mark.parametrize("path", ["src/a.py", "tests/x.py", "README.md"])
def test_an_invalid_configuration_denies_everything_inside_the_root_with_the_error(
        monkeypatch, capsys, config_file, trail, path):
    config_file("{")
    assert run_hook(monkeypatch, REPO_ROOT / path) == 2
    err = capsys.readouterr().err
    assert ".actuarii.json" in err
    assert "not valid JSON" in err


def test_an_invalid_configuration_allows_what_is_outside_the_root(monkeypatch, tmp_path, config_file, trail):
    config_file("{")
    assert run_hook(monkeypatch, tmp_path.resolve() / "x.py") == 0


def test_the_configuration_file_stays_subject_to_a_receipt_when_it_is_invalid(monkeypatch, config_file, trail):
    config_file("{")
    assert run_hook(monkeypatch, REPO_ROOT / ".actuarii.json") == 2
    grant(".actuarii.json")
    assert run_hook(monkeypatch, REPO_ROOT / ".actuarii.json") == 0


def test_an_invalid_configuration_leaves_the_default_window_for_its_own_file(
        monkeypatch, config_file, trail, isolate_audit_db):
    config_file("{")
    grant(".actuarii.json")
    age(isolate_audit_db, ".actuarii.json", 600)
    assert run_hook(monkeypatch, REPO_ROOT / ".actuarii.json") == 0
    age(isolate_audit_db, ".actuarii.json", 1000)
    assert run_hook(monkeypatch, REPO_ROOT / ".actuarii.json") == 2


# T5: every denial names its rule

def test_a_denial_names_the_path_the_rule_the_source_the_window_and_the_call(
        monkeypatch, capsys, config_file, trail):
    config_file(CONFIG)
    target = REPO_ROOT / "src" / "a.py"
    assert run_hook(monkeypatch, target) == 2
    err = capsys.readouterr().err
    for needle in (
        str(target),
        'governed_paths entry "src/**"',
        "source: .actuarii.json",
        "window: 60 s",
        "no recent EXECUTE_SAFE",
        f"mcp__boundary-validator__validate_proposal with target_file={target}",
    ):
        assert needle in err, needle


def test_the_configuration_file_is_denied_under_its_own_rule(monkeypatch, capsys, config_file, trail):
    config_file(CONFIG)
    assert run_hook(monkeypatch, REPO_ROOT / ".actuarii.json") == 2
    err = capsys.readouterr().err
    assert OWN_RULE in err
    assert "window: 60 s" in err


@pytest.mark.parametrize("content, path", [
    pytest.param(CONFIG, "src/a.py", id="pattern"),
    pytest.param(CONFIG, ".actuarii.json", id="own-file"),
    pytest.param(WITH_REGISTRY, "contracts/registry.json", id="registry"),
    pytest.param(None, "CLAUDE.md", id="built-in"),
    pytest.param("{", "src/a.py", id="invalid"),
])
def test_no_denial_cites_agents_clauses_or_names_traianus(monkeypatch, capsys, config_file, trail, content, path):
    if content is not None:
        config_file(content)
    assert run_hook(monkeypatch, REPO_ROOT / path) == 2
    err = capsys.readouterr().err
    assert err
    assert not FOREIGN.search(err), err
