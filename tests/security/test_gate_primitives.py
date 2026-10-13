"""The write gate decides on the primitives of the file a write produces (tools/hooks/require_boundary_validation.py).

For Edit, MultiEdit and Write on a governed .py path, once the receipts pass, the hook computes the exact result
from the file as it is, parses it with ast and denies when it does not parse or introduces a primitive the file
did not have. The hook runs in process, driven through `main` on a replaced stdin, in a repository of its own
under tmp_path that governs `src/**`. The sources are string literals: nothing here imports a primitive.
"""
import hashlib
import io
import json
import sys
import uuid

import pytest

from tools.boundary_validator import hook_gate, validator
from tools.boundary_validator.validator import validate_proposal
from tools.hooks import require_boundary_validation

CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 60,
}
VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def repo(monkeypatch, tmp_path, config_file):
    root = tmp_path.resolve() / "repo"
    (root / "src").mkdir(parents=True)
    (root / "lib").mkdir()
    for module in (hook_gate, validator, require_boundary_validation):
        monkeypatch.setattr(module, "REPO_ROOT", root)
    config_file(CONFIG)
    return root


@pytest.fixture
def put(repo):
    def write_file(relative, content):
        path = repo / relative
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    return write_file


@pytest.fixture
def receipt(repo):
    """A receipt for one exact change, written as the validator writes it, without its own check."""
    def issue(relative, old, new):
        validator._persist_receipt(str(uuid.uuid4()), str(repo / relative), sha(old), sha(new))

    return issue


@pytest.fixture
def run(monkeypatch, repo):
    def call(tool, tool_input):
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        return require_boundary_validation.main()

    return call


def edit(repo, relative, old, new, **extra):
    return "Edit", {"file_path": str(repo / relative), "old_string": old, "new_string": new, **extra}


def multi_edit(repo, relative, *pairs):
    return "MultiEdit", {"file_path": str(repo / relative),
                         "edits": [{"old_string": old, "new_string": new} for old, new in pairs]}


def write(repo, relative, content):
    return "Write", {"file_path": str(repo / relative), "content": content}


# T4: a receipt is not enough when the result introduces a primitive


@pytest.mark.parametrize("new", [
    "import subprocess",
    "from socket import socket",
    "import os\nos.system('id')",
    "from os import popen",
    "value = eval",
    "__import__('x')",
])
def test_an_edit_with_a_receipt_whose_result_introduces_a_primitive_is_denied(repo, put, receipt, run, capsys, new):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", new)
    assert run(*edit(repo, "src/a.py", "value = 1", new)) == 2
    err = capsys.readouterr().err
    assert err.startswith("[require_boundary_validation]")
    assert str(repo / "src" / "a.py") in err
    assert 'governed_paths entry "src/**"' in err
    assert "(source: .actuarii.json)" in err
    assert "AGENTS" not in err


def test_the_denial_names_the_new_primitives_sorted(repo, put, receipt, run, capsys):
    put("src/a.py", "value = 1\n")
    new = "import socket\nimport os\nos.system('id')\nvalue = eval"
    receipt("src/a.py", "value = 1", new)
    assert run(*edit(repo, "src/a.py", "value = 1", new)) == 2
    err = capsys.readouterr().err
    assert "eval, import socket, os.system" in err


def test_the_same_edit_without_a_primitive_passes_with_its_receipt(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", "value = 2")
    assert run(*edit(repo, "src/a.py", "value = 1", "value = 2")) == 0


def test_a_missing_receipt_is_still_what_the_gate_names_first(repo, put, receipt, run, capsys):
    put("src/a.py", "value = 1\n")
    receipt("src/other.py", "value = 1", "value = 2")
    assert run(*edit(repo, "src/a.py", "value = 1", "import subprocess")) == 2
    assert "no recent EXECUTE_SAFE receipt" in capsys.readouterr().err


def test_an_uppercase_extension_is_checked_too(repo, receipt, run):
    receipt("src/B.PY", "", "import subprocess")
    assert run(*write(repo, "src/B.PY", "import subprocess")) == 2


# T5: two receipts clean on the file they were validated against cannot be chained


def test_the_second_of_two_chained_receipts_is_checked_against_the_file_the_first_left(repo, put, run, capsys):
    put("src/a.py", "import aa_bb\n")
    first = validate_proposal(json.dumps({
        "Intent_Class": "FIX", "Target_File": "src/a.py", "Topological_Grounding": "aa_",
        "Implementation_Block": "subp", "Safety_Abort": "NONE",
        "Rationale": "A test proposal."}), "src/a.py")
    second = validate_proposal(json.dumps({
        "Intent_Class": "FIX", "Target_File": "src/a.py", "Topological_Grounding": "bb",
        "Implementation_Block": "rocess", "Safety_Abort": "NONE",
        "Rationale": "A test proposal."}), "src/a.py")
    assert first["final_decision"] == second["final_decision"] == "EXECUTE_SAFE"
    assert run(*edit(repo, "src/a.py", "aa_", "subp")) == 0
    put("src/a.py", "import subpbb\n")
    assert run(*edit(repo, "src/a.py", "bb", "rocess")) == 2
    assert "import subprocess" in capsys.readouterr().err


# T6: the edits of a MultiEdit are applied in order, and the result is what counts


def test_a_multi_edit_clean_edit_by_edit_but_not_together_is_denied(repo, put, receipt, run, capsys):
    put("src/a.py", "import aa_bb\n")
    receipt("src/a.py", "aa_", "subp")
    receipt("src/a.py", "bb", "rocess")
    assert run(*multi_edit(repo, "src/a.py", ("aa_", "subp"), ("bb", "rocess"))) == 2
    assert "import subprocess" in capsys.readouterr().err


def test_a_multi_edit_without_a_primitive_passes_with_its_receipts(repo, put, receipt, run):
    put("src/a.py", "one = 1\ntwo = 2\n")
    receipt("src/a.py", "one", "uno")
    receipt("src/a.py", "two", "dos")
    assert run(*multi_edit(repo, "src/a.py", ("one", "uno"), ("two", "dos"))) == 0


def test_a_multi_edit_edit_that_applies_only_after_an_earlier_one_is_checked_in_order(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", "import socket")
    receipt("src/a.py", "import socket", "value = 1")
    assert run(*multi_edit(repo, "src/a.py", ("value = 1", "import socket"), ("import socket", "value = 1"))) == 0


# T7: Write and results that do not parse


@pytest.mark.parametrize("content", ["import subprocess\n", "x = 1\nfrom http import client\n", "run = exec\n"])
def test_a_write_that_introduces_a_primitive_is_denied_with_its_receipt(repo, put, receipt, run, capsys, content):
    put("src/a.py", "x = 1\n")
    receipt("src/a.py", "", content)
    assert run(*write(repo, "src/a.py", content)) == 2
    assert capsys.readouterr().err.startswith("[require_boundary_validation]")


def test_a_write_to_a_new_file_that_introduces_a_primitive_is_denied(repo, receipt, run):
    receipt("src/new.py", "", "import socket\n")
    assert run(*write(repo, "src/new.py", "import socket\n")) == 2


def test_a_write_without_a_primitive_passes_with_its_receipt(repo, receipt, run):
    receipt("src/new.py", "", "value = 1\n")
    assert run(*write(repo, "src/new.py", "value = 1\n")) == 0


def test_a_write_that_does_not_parse_is_denied_naming_the_python_of_the_hook(repo, put, receipt, run, capsys):
    put("src/a.py", "x = 1\n")
    receipt("src/a.py", "", "def broken(:\n")
    assert run(*write(repo, "src/a.py", "def broken(:\n")) == 2
    err = capsys.readouterr().err
    assert err.startswith("[require_boundary_validation]")
    assert "does not parse" in err
    assert VERSION in err
    assert 'governed_paths entry "src/**"' in err


def test_an_edit_whose_result_does_not_parse_is_denied(repo, put, receipt, run, capsys):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", "value = (")
    assert run(*edit(repo, "src/a.py", "value = 1", "value = (")) == 2
    assert VERSION in capsys.readouterr().err


def test_a_result_with_a_nul_byte_is_denied_not_allowed(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", "value = 1\x00")
    assert run(*edit(repo, "src/a.py", "value = 1", "value = 1\x00")) == 2


def test_an_edit_with_an_empty_old_string_gives_its_new_string_as_the_whole_result(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "", "import socket\n")
    assert run(*edit(repo, "src/a.py", "", "import socket\n")) == 2


def test_an_edit_that_creates_a_file_is_checked_as_a_whole(repo, receipt, run):
    receipt("src/new.py", "", "import socket\n")
    assert run(*edit(repo, "src/new.py", "", "import socket\n")) == 2


def test_replace_all_decides_how_many_occurrences_the_result_has(repo, put, receipt, run):
    put("src/a.py", "# q\nq\n")
    receipt("src/a.py", "q", "import subprocess")
    assert run(*edit(repo, "src/a.py", "q", "import subprocess")) == 0
    assert run(*edit(repo, "src/a.py", "q", "import subprocess", replace_all=True)) == 2


def test_a_current_file_that_is_not_utf8_is_denied(repo, put, receipt, run, capsys):
    put("src/a.py", b"value = '\xff\xfe'\n")
    receipt("src/a.py", "value", "other")
    assert run(*edit(repo, "src/a.py", "value", "other")) == 2
    assert "UTF-8" in capsys.readouterr().err


# T8: a file that does not parse gives the empty baseline


def test_fixing_the_syntax_of_a_file_that_imports_a_primitive_does_not_let_the_import_through(
        repo, put, receipt, run, capsys):
    put("src/a.py", "import socket\ndef broken(:\n")
    receipt("src/a.py", "def broken(:", "def fixed():\n    pass")
    assert run(*edit(repo, "src/a.py", "def broken(:", "def fixed():\n    pass")) == 2
    assert "import socket" in capsys.readouterr().err


# T9: a primitive the file already has stays editable


@pytest.mark.parametrize("new", [
    "subprocess.run(['id'])\nsubprocess.run(['ls'])",
    "import subprocess as sp\nvalue = sp",
    "from subprocess import run\nvalue = run",
])
def test_an_edit_that_adds_a_use_of_a_primitive_the_file_already_has_passes(repo, put, receipt, run, new):
    put("src/a.py", "import subprocess\nsubprocess.run(['id'])\n")
    receipt("src/a.py", "subprocess.run(['id'])", new)
    assert run(*edit(repo, "src/a.py", "subprocess.run(['id'])", new)) == 0


def test_a_write_that_keeps_the_primitives_of_the_file_passes(repo, put, receipt, run):
    put("src/a.py", "import subprocess\n")
    receipt("src/a.py", "", "import subprocess\nvalue = 1\n")
    assert run(*write(repo, "src/a.py", "import subprocess\nvalue = 1\n")) == 0


# T10: what the check does not reach


def test_a_governed_file_that_is_not_python_is_not_checked(repo, put, receipt, run):
    put("src/notes.md", "text\n")
    receipt("src/notes.md", "text", "import subprocess\ndef broken(:")
    assert run(*edit(repo, "src/notes.md", "text", "import subprocess\ndef broken(:")) == 0
    receipt("src/notes.md", "", "import socket")
    assert run(*write(repo, "src/notes.md", "import socket")) == 0


def test_a_notebook_edit_is_not_checked(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "", "import subprocess")
    assert run("NotebookEdit", {"notebook_path": str(repo / "src" / "a.py"), "new_source": "import subprocess"}) == 0


def test_an_ungoverned_python_file_is_not_checked_and_needs_no_receipt(repo, put, run):
    put("lib/free.py", "value = 1\n")
    assert run(*edit(repo, "lib/free.py", "value = 1", "import subprocess")) == 0
    assert run(*write(repo, "lib/free.py", "def broken(:")) == 0


@pytest.mark.parametrize("unapplicable", ["absent from the file", "value = 2"])
def test_an_edit_whose_old_string_is_not_in_the_file_writes_nothing_and_is_not_checked(
        repo, put, receipt, run, unapplicable):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", unapplicable, "import subprocess")
    assert run(*edit(repo, "src/a.py", unapplicable, "import subprocess")) == 0


def test_an_edit_on_a_file_that_does_not_exist_with_an_old_string_writes_nothing_and_is_not_checked(
        repo, receipt, run):
    receipt("src/gone.py", "value = 1", "import subprocess")
    assert run(*edit(repo, "src/gone.py", "value = 1", "import subprocess")) == 0


def test_a_multi_edit_with_an_edit_that_cannot_apply_writes_nothing_and_is_not_checked(repo, put, receipt, run):
    put("src/a.py", "value = 1\n")
    receipt("src/a.py", "value = 1", "import subprocess")
    receipt("src/a.py", "absent", "x")
    assert run(*multi_edit(repo, "src/a.py", ("value = 1", "import subprocess"), ("absent", "x"))) == 0


def test_a_tool_of_the_third_class_keeps_the_receipt_per_file_and_no_primitive_check(repo, put, run):
    put("src/a.py", "value = 1\n")
    tool_input = {"path": str(repo / "src" / "a.py"), "content": "import subprocess"}
    assert run("mcp__fs__write_file", tool_input) == 2
    clean = json.dumps({"Intent_Class": "DOC", "Target_File": "src/a.py", "Topological_Grounding": "value",
                        "Implementation_Block": "other", "Safety_Abort": "NONE",
                        "Rationale": "A test proposal."})
    assert validate_proposal(clean, "src/a.py")["final_decision"] == "EXECUTE_SAFE"
    assert run("mcp__fs__write_file", tool_input) == 0
