"""Bash hook (tools/hooks/deny_python_escapes.py, AGENTS 2.5): the ways of reaching a Python
interpreter around the tools/bin shim are denied (exit 2, fail closed); every other command passes.

Normative: AGENTS.md 2.5, 6.2
"""
import ast
import io
import json
import sys
from pathlib import Path

import pytest

from tools.hooks.deny_python_escapes import main

HOOK = Path(__file__).resolve().parents[2] / "tools" / "hooks" / "deny_python_escapes.py"

DATA_HEREDOC = """python3 tools/audit/context_pack.py <<'EOF'
{task: it's a task, note: PATH=/x /usr/bin/python3 -c}
EOF
"""
COMMIT_HEREDOC = """git commit -m "$(cat <<'EOF'
feat: it's PATH=/x via /usr/bin/python3
EOF
)"
"""
TAB_HEREDOC = "cat <<-'EOF'\n\tit's data\n\tEOF"
SHELL_HEREDOC = """bash <<'EOF'
/usr/bin/python3 -c x
EOF
"""
PIPED_HEREDOC = """cat <<'EOF' | sh
/usr/bin/python3 x
EOF
"""
EXPANDING_HEREDOC = """cat <<EOF
$(/usr/bin/python3 -c x)
EOF
"""
UNTERMINATED_HEREDOC = """cat <<'EOF'
/usr/bin/python3 x
"""
SHELL_HEREDOC_WITH_APOSTROPHE = """bash <<'EOF'
it's
EOF
"""
NEWLINE_SEPARATED = """git status
/usr/bin/python3 x
"""
NESTED_QUOTES = """sh -c '/usr/bin/python3 -c "print(1)"'"""
WRITTEN_TO_FILE = """cat > /tmp/x.sh <<'EOF'
/usr/bin/python3 -c x
EOF
chmod +x /tmp/x.sh
/tmp/x.sh
"""
APPENDED_TO_FILE = WRITTEN_TO_FILE.replace("cat >", "cat >>")
TEED_TO_FILE = """cat <<'EOF' | tee /tmp/x.sh
/usr/bin/python3 -c x
EOF
"""
PATH_WRITTEN_TO_FILE = """cat > /tmp/x.sh <<'EOF'
export PATH=/usr/bin:$PATH
EOF
"""
PROSE_WRITTEN_TO_FILE = """cat > /tmp/notes.md <<'EOF'
it's prose
EOF
"""
CONTRACT_HEREDOC = """python3 tools/audit/delegation_contract.py contract <<'EOF'
{"problem": "it's data: export PATH=/x"}
EOF
"""
HARMLESS_FILE_HEREDOC = """cat > /tmp/notes.txt <<'EOF'
a harmless note about the shim
EOF
"""
CONTRACT_HEREDOC_MERGING_STDERR = CONTRACT_HEREDOC.replace("contract <<'EOF'", "contract <<'EOF' 2>&1")

PERMITTED = [
    "git status",
    "git commit -m 'fix: a message'",
    "pytest tests/ -q",
    "ruff check .",
    "npm --prefix frontend run typecheck",
    "python3 --version",
    "tools/bin/python3 tools/audit/x.py",
    "/work/repo/tools/bin/python3 tools/audit/x.py",
    "git grep python3",
    "echo python3 python python3.11",
    "command -v python3",
    "git status && python3 tools/audit/x.py",
    "env FOO=1 pytest tests/ -q && ls -i",
    "env FOO=1 pytest tests/ -q\nls -i",
    "pyenv\nexec ls",
    DATA_HEREDOC,
    COMMIT_HEREDOC,
    TAB_HEREDOC,
    CONTRACT_HEREDOC,
    CONTRACT_HEREDOC_MERGING_STDERR,
    HARMLESS_FILE_HEREDOC,
]

DENIED = [
    ("/usr/bin/python3 -c x", "R1", "/usr/bin/python3"),
    ("/opt/homebrew/bin/python3.12 x", "R1", "/opt/homebrew/bin/python3.12"),
    ("~/.pyenv/versions/3.11.6/bin/python3 x", "R1", "~/.pyenv/versions/3.11.6/bin/python3"),
    ("$HOME/.pyenv/shims/python3 x", "R1", "$HOME/.pyenv/shims/python3"),
    ("./venv/bin/python x", "R1", "./venv/bin/python"),
    ("python3.12 x", "R2", "python3.12"),
    ("pypy3 x", "R2", "pypy3"),
    ("ipython", "R2", "ipython"),
    ("pyenv exec python3 x", "R3", "pyenv"),
    ("PATH=/usr/bin python3 x", "R4", "PATH=/usr/bin"),
    ("export PATH=/usr/bin:$PATH", "R4", "PATH=/usr/bin:$PATH"),
    ("env PATH=/usr/bin python3 x", "R4", "PATH=/usr/bin"),
    ("unset PATH", "R4", "unset"),
    ("unset -v PATH", "R4", "unset"),
    ("env -i python3 x", "R5", "env"),
    ("env --ignore-environment python3 x", "R5", "env"),
    ("env - python3 x", "R5", "env"),
    ("env -u PATH python3 x", "R5", "env"),
    ("env -uPATH python3 x", "R5", "env"),
    ("env --unset=PATH python3 x", "R5", "env"),
    ("env --unset PATH python3 x", "R5", "env"),
    ("env -P /usr/bin python3 x", "R5", "env"),
    ("/usr/bin/env -i python3 x", "R5", "env"),
    ("command -p python3 x", "R6", "command"),
    (NESTED_QUOTES, "R1", "/usr/bin/python3"),
    ("sh -c 'PATH=/usr/bin python3 x'", "R4", "PATH=/usr/bin"),
    ("sh -c 'python3.12 x'", "R2", "python3.12"),
    ("bash -c 'echo hi; env -i python3 x'", "R5", "env"),
    ("git status && /usr/bin/python3 x", "R1", "/usr/bin/python3"),
    ("git status; /usr/bin/python3 x", "R1", "/usr/bin/python3"),
    (NEWLINE_SEPARATED, "R1", "/usr/bin/python3"),
    ("x#; /usr/bin/python3 -c y", "R1", "/usr/bin/python3"),
    (SHELL_HEREDOC, "R1", "/usr/bin/python3"),
    (PIPED_HEREDOC, "R1", "/usr/bin/python3"),
    (EXPANDING_HEREDOC, "R1", "/usr/bin/python3"),
    (UNTERMINATED_HEREDOC, "R1", "/usr/bin/python3"),
    (WRITTEN_TO_FILE, "R1", "/usr/bin/python3"),
    (APPENDED_TO_FILE, "R1", "/usr/bin/python3"),
    (TEED_TO_FILE, "R1", "/usr/bin/python3"),
    (PATH_WRITTEN_TO_FILE, "R4", "PATH=/usr/bin:$PATH"),
    (PROSE_WRITTEN_TO_FILE, "unverifiable", ""),
    ("echo 'unbalanced", "unverifiable", ""),
    (SHELL_HEREDOC_WITH_APOSTROPHE, "unverifiable", ""),
]


def verdict(monkeypatch, capsys, raw):
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
    code = main()
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def bash(monkeypatch, capsys, command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return verdict(monkeypatch, capsys, json.dumps(payload))


# T9: what passes


@pytest.mark.parametrize("command", PERMITTED)
def test_permitted_command_exits_0_in_silence(monkeypatch, capsys, command):
    assert bash(monkeypatch, capsys, command) == (0, "", "")


@pytest.mark.parametrize("tool", ["Edit", "Write", "Read", "Grep"])
def test_other_tools_are_not_looked_at(monkeypatch, capsys, tool):
    payload = {"tool_name": tool, "tool_input": {"file_path": "/usr/bin/python3", "pattern": "PATH=x"}}
    assert verdict(monkeypatch, capsys, json.dumps(payload)) == (0, "", "")


# T10: what is denied


@pytest.mark.parametrize("command, rule, word", DENIED)
def test_denied_command_exits_2_naming_the_rule_and_the_word(monkeypatch, capsys, command, rule, word):
    code, out, err = bash(monkeypatch, capsys, command)
    assert (code, out) == (2, "")
    assert rule in err and word in err and "AGENTS 2.5" in err


@pytest.mark.parametrize("command, word", [
    ('git commit -m "docs: mention ipython"', "ipython"),
    ("grep -e python3.12 file", "python3.12"),
    ("sh -c 'python3.12 x'", "python3.12"),
])
def test_r2_denies_a_mere_mention_of_an_uncovered_interpreter(monkeypatch, capsys, command, word):
    """Declared limit of the hook: R2 applies to the words of a quoted argument too, so a commit
    message or a grep pattern that only names such an interpreter is denied. Changing this is a
    deliberate act; sh -c 'python3.12 x' is caught by the same second pass."""
    code, out, err = bash(monkeypatch, capsys, command)
    assert (code, out) == (2, "")
    assert "R2" in err and word in err


# T11: fail closed


@pytest.mark.parametrize("raw", [
    "",
    "not json",
    "[1, 2]",
    "null",
    '{"tool_name": "Bash"}',
    '{"tool_name": "Bash", "tool_input": {}}',
    '{"tool_name": "Bash", "tool_input": {"command": 5}}',
    '{"tool_name": "Bash", "tool_input": {"command": null}}',
    '{"tool_name": "Bash", "tool_input": "git status"}',
])
def test_malformed_input_exits_2_with_a_message(monkeypatch, capsys, raw):
    code, out, err = verdict(monkeypatch, capsys, raw)
    assert (code, out) == (2, "")
    assert err


# T12: startup surface


def hook_tree():
    return ast.parse(HOOK.read_text(encoding="utf-8"), feature_version=(3, 9))


def test_hook_imports_only_the_standard_library():
    roots = set()
    for node in ast.walk(hook_tree()):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add("." * node.level + (node.module or "").split(".")[0])
    assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)


def test_hook_postpones_annotations_and_parses_as_python_39():
    """An import failure exits 1, which the harness reads as a broken hook, not a denial."""
    assert any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in hook_tree().body)


def test_hook_exits_with_its_verdict():
    assert "sys.exit(main())" in HOOK.read_text(encoding="utf-8")
