"""The write gate decides by tool class, not by a list of writers (tools/hooks/require_boundary_validation.py).

Known writers (Edit, MultiEdit, Write, NotebookEdit) need a receipt for the governed path in their path
field, and are denied without that field. Known tools that write no file pass, the boundary validator
included. Any other tool is denied when a string of its input resolves to a governed path and no receipt
covers it. The hook runs in process, driven through `main` on a replaced stdin, against a configuration that
governs `src/**`.
"""
import io
import json
import shlex
import sys

import pytest

from tools.boundary_validator.hook_gate import REPO_ROOT
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
GOVERNED = str(REPO_ROOT / "src" / "a.py")
FREE = str(REPO_ROOT / "docs" / "x.md")
WRITERS = [("Edit", "file_path"), ("MultiEdit", "file_path"), ("Write", "file_path"),
           ("NotebookEdit", "notebook_path")]
NON_WRITERS = ["Read", "Grep", "Glob", "LS", "NotebookRead", "Bash", "BashOutput", "KillShell", "WebFetch",
               "WebSearch", "TodoWrite", "Task", "Agent", "Skill", "ToolSearch", "AskUserQuestion",
               "EnterPlanMode", "ExitPlanMode", "SendMessage", "mcp__boundary-validator__validate_proposal"]
UNKNOWN = "mcp__fs__write_file"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


@pytest.fixture
def gate(monkeypatch, config_file):
    config_file(CONFIG)
    grant("docs/decoy.md")

    def run(tool, tool_input, **extra):
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input, **extra})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        return require_boundary_validation.main()

    return run


def grant(target):
    proposal = json.dumps({"Intent_Class": "DOC", "Target_File": target, "Topological_Grounding": "q",
                           "Implementation_Block": "b", "Safety_Abort": "NONE"})
    assert validate_proposal(proposal, target)["final_decision"] == "EXECUTE_SAFE"


# What each writer writes, as the receipt that grant() leaves covers it: the quote is the old_string and the
# block the new_string, or the block alone is the content or the new_source.
CONTENT = {
    "Edit": {"old_string": "q", "new_string": "b"},
    "MultiEdit": {"edits": [{"old_string": "q", "new_string": "b"}]},
    "Write": {"content": "b"},
    "NotebookEdit": {"new_source": "b"},
}


# T1: a known writer needs a receipt for the governed path, and a path field


@pytest.mark.parametrize("tool, field", WRITERS)
def test_a_writer_on_a_governed_path_is_denied_without_a_receipt(gate, tool, field):
    assert gate(tool, {field: GOVERNED, **CONTENT[tool]}) == 2


@pytest.mark.parametrize("tool, field", WRITERS)
def test_a_writer_on_a_governed_path_is_allowed_with_a_receipt(gate, tool, field):
    grant("src/a.py")
    assert gate(tool, {field: GOVERNED, **CONTENT[tool]}) == 0


@pytest.mark.parametrize("tool, field", WRITERS)
def test_a_writer_on_an_ungoverned_path_is_allowed_without_a_receipt(gate, tool, field):
    assert gate(tool, {field: FREE}) == 0


@pytest.mark.parametrize("tool, field", WRITERS)
@pytest.mark.parametrize("tool_input", [
    {}, {"file_path": ""}, {"notebook_path": ""}, {"file_path": None}, {"notebook_path": None},
    {"file_path": 7}, {"notebook_path": ["src/a.py"]}, {"file_path": {"path": "src/a.py"}}, None, "src/a.py",
])
def test_a_writer_without_a_usable_path_field_is_denied(gate, tool, field, tool_input):
    assert gate(tool, tool_input) == 2


@pytest.mark.parametrize("tool, field", WRITERS)
def test_a_writer_whose_other_field_names_a_governed_path_still_needs_its_own(gate, tool, field):
    other = "notebook_path" if field == "file_path" else "file_path"
    assert gate(tool, {other: GOVERNED, field: ""}) == 2


def test_a_payload_that_is_not_an_object_is_denied(monkeypatch, config_file):
    config_file(CONFIG)
    monkeypatch.setattr(sys, "stdin", io.StringIO("[]"))
    assert require_boundary_validation.main() == 2


# T2: tools that write no file pass, the validator included


@pytest.mark.parametrize("tool", NON_WRITERS)
def test_a_known_tool_that_writes_no_file_passes_with_a_governed_path_in_its_input(gate, tool):
    assert gate(tool, {"file_path": GOVERNED, "path": GOVERNED, "target_file": GOVERNED,
                       "notebook_path": GOVERNED, "args": [GOVERNED]}) == 0


def test_the_validator_with_a_governed_target_file_passes_without_a_receipt(gate):
    tool_input = {"proposal": "{}", "target_file": GOVERNED}
    assert gate("mcp__boundary-validator__validate_proposal", tool_input) == 0


# T3: any other tool needs a receipt when its input names a governed path

LOCATIONS = [
    ("flat", {"path": GOVERNED}, "tool_input.path"),
    ("in a list", {"args": [{"mode": "w"}, {"path": GOVERNED}]}, "tool_input.args[1].path"),
    ("in a dictionary", {"options": {"output": {"file": GOVERNED}}}, "tool_input.options.output.file"),
    ("in a list of strings", {"files": ["docs/x.md", GOVERNED]}, "tool_input.files[1]"),
    ("relative to the root", {"path": "src/a.py"}, "tool_input.path"),
]


@pytest.mark.parametrize("_name, tool_input, _where", LOCATIONS, ids=[item[0] for item in LOCATIONS])
def test_an_unknown_tool_naming_a_governed_path_is_denied_without_a_receipt(gate, _name, tool_input, _where):
    assert gate(UNKNOWN, tool_input) == 2


@pytest.mark.parametrize("_name, tool_input, _where", LOCATIONS, ids=[item[0] for item in LOCATIONS])
def test_an_unknown_tool_naming_a_governed_path_is_allowed_with_a_receipt(gate, _name, tool_input, _where):
    grant("src/a.py")
    assert gate(UNKNOWN, tool_input) == 0


def test_a_relative_path_is_resolved_against_the_cwd_of_the_payload(gate):
    tool_input = {"path": "deep/b.py"}
    assert gate(UNKNOWN, tool_input, cwd=str(REPO_ROOT / "src")) == 2
    assert gate(UNKNOWN, tool_input, cwd=str(REPO_ROOT / "docs")) == 0
    grant("src/deep/b.py")
    assert gate(UNKNOWN, tool_input, cwd=str(REPO_ROOT / "src")) == 0


@pytest.mark.parametrize("cwd", [None, "", 7, "src", "docs"])
def test_a_cwd_that_is_not_an_absolute_path_leaves_a_relative_path_to_the_root(gate, cwd):
    assert gate(UNKNOWN, {"path": "src/a.py"}, cwd=cwd) == 2


@pytest.mark.parametrize("_name, tool_input, where", LOCATIONS[:4], ids=[item[0] for item in LOCATIONS[:4]])
def test_the_denial_names_the_tool_the_field_the_file_the_rule_and_the_call(
        gate, capsys, _name, tool_input, where):
    assert gate(UNKNOWN, tool_input) == 2
    err = capsys.readouterr().err
    assert UNKNOWN in err
    assert where in err
    assert GOVERNED in err
    assert "src/**" in err
    assert "source: .actuarii.json" in err
    assert "window: 60 s" in err
    assert f"mcp__boundary-validator__validate_proposal with target_file={GOVERNED}" in err
    assert "does not know" in err
    assert "AGENTS" not in err


def test_an_unknown_tool_naming_an_ungoverned_path_passes(gate):
    assert gate(UNKNOWN, {"path": FREE, "args": [FREE, "docs/x.md"]}) == 0


def test_an_unknown_tool_naming_a_path_outside_the_root_passes(gate, tmp_path):
    assert gate(UNKNOWN, {"path": str(tmp_path / "src" / "a.py")}) == 0


@pytest.mark.parametrize("value", [
    "src",
    "a.py",
    "src/a.py\nsrc/b.py",
    GOVERNED + "\n",
    "src/a.py\0",
    "src/" + "x" * 4100,
    "",
    7,
    True,
    None,
    ["src"],
    {"src": None},
])
def test_strings_that_are_not_path_candidates_pass(gate, value):
    assert gate(UNKNOWN, {"path": value, "args": [value]}) == 0


@pytest.mark.parametrize("tool_input", [{}, None, "just text", ["src"], 3, {"args": []}])
def test_an_unknown_tool_without_a_path_in_its_input_passes(gate, tool_input):
    assert gate(UNKNOWN, tool_input) == 0


def test_a_missing_tool_name_is_an_unknown_tool(monkeypatch, config_file):
    config_file(CONFIG)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"path": GOVERNED}})))
    assert require_boundary_validation.main() == 2


def test_a_resolution_failure_denies_naming_the_tool_and_the_field(monkeypatch, capsys, config_file):
    config_file(CONFIG)
    payload = json.dumps({"tool_name": UNKNOWN, "tool_input": {"args": [{"path": GOVERNED}]}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))

    def refuse(*_args):
        raise PermissionError("denied by the test")

    assert require_boundary_validation.main(samefile=refuse) == 2
    err = capsys.readouterr().err
    assert UNKNOWN in err
    assert "tool_input.args[0].path" in err
    assert "denied by the test" in err


def test_a_deeply_nested_input_does_not_escape_the_gate(monkeypatch, config_file):
    config_file(CONFIG)
    depth = 5000
    nested = "[" * depth + json.dumps(GOVERNED) + "]" * depth
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"tool_name": "%s", "tool_input": {"x": %s}}' % (UNKNOWN, nested)))
    assert require_boundary_validation.main() == 2


# T3b: the configuration decides, and an invalid one denies


@pytest.mark.parametrize("tool, tool_input", [
    ("Write", {"file_path": GOVERNED}),
    (UNKNOWN, {"path": GOVERNED}),
    (UNKNOWN, {"args": [{"path": str(REPO_ROOT / "docs" / "x.md")}]}),
])
def test_with_an_invalid_configuration_a_path_inside_the_root_is_denied_with_the_error(
        gate, config_file, capsys, tool, tool_input):
    config_file("{not json")
    assert gate(tool, tool_input) == 2
    assert "configuration is invalid" in capsys.readouterr().err


def test_with_an_invalid_configuration_a_path_outside_the_root_and_a_non_path_pass(gate, config_file, tmp_path):
    config_file("{not json")
    assert gate(UNKNOWN, {"path": str(tmp_path / "x.py"), "mode": "w"}) == 0


def test_without_a_configuration_the_built_in_minimum_governs_an_unknown_tool(gate, monkeypatch, tmp_path):
    from tools import project_config

    monkeypatch.setattr(project_config, "CONFIG_PATH", tmp_path / "absent.json")
    assert gate(UNKNOWN, {"path": str(REPO_ROOT / "AGENTS.md")}) == 2


# T5: the hooks are launched for every tool


def test_the_write_hooks_are_launched_for_every_tool():
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    [group] = [item for item in groups
               if any("require_boundary_validation.py" in hook["command"] for hook in item["hooks"])]
    assert group["matcher"] == "*"
    assert [shlex.split(hook["command"]) for hook in group["hooks"]] == [
        ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/require_boundary_validation.py"],
        ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/require_contract_context.py"],
    ]
