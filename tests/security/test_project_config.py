"""The project configuration, .actuarii.json (tools/project_config.py).

The write gate takes the paths it governs and the receipt window from this file. It is read strictly: every
deviation from the schema is an error with its cause, never a silent default. Without the file the gate governs a
built-in minimum and says so. The file itself is always governed.

The module is on the gate's startup path: it imports only the standard library and is importable by a
Python 3.9 interpreter, because an import error exits 1, which the harness reads as a broken hook and not as a
denial.
"""
import ast
import json
import shutil
import sys
from pathlib import Path

import pytest

from tools import project_config
from tools.audit.run_process import run
from tools.project_config import ConfigError, governance, load

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "project_config.py"
BUILT_IN = "built-in minimum (no .actuarii.json)"
OWN_RULE = "always governed: the project configuration"
VALID = {
    "schema": "actuarii-config/1",
    "governed_paths": ["src/**", "docs/*.md"],
    "python_script_dirs": ["scripts", "tools/sub", "."],
    "contract_registry": "contracts/registry.json",
    "receipt_window_seconds": 60,
}
REGISTRY_RULE = "always governed: the contract registry"


def text(**changes):
    return json.dumps({**VALID, **changes})


def without(key):
    return json.dumps({name: value for name, value in VALID.items() if name != key})


def window_as(literal):
    return (
        '{"schema": "actuarii-config/1", "governed_paths": ["a"], "python_script_dirs": [], '
        '"contract_registry": null, "receipt_window_seconds": %s}' % literal
    )


# T1: a case per validation rule

INVALID = [
    pytest.param("{", "not valid JSON", id="not-json"),
    pytest.param("", "not valid JSON", id="empty"),
    pytest.param(
        '{"schema": "actuarii-config/1", "schema": "actuarii-config/1", '
        '"governed_paths": ["a"], "python_script_dirs": [], "contract_registry": null, '
        '"receipt_window_seconds": 60}',
        "duplicate key 'schema'", id="duplicate-key"),
    pytest.param(window_as("NaN"), "NaN", id="nan"),
    pytest.param(window_as("Infinity"), "Infinity", id="infinity"),
    pytest.param(window_as("-Infinity"), "Infinity", id="negative-infinity"),
    pytest.param("[]", "JSON object", id="array"),
    pytest.param('"x"', "JSON object", id="string"),
    pytest.param(text(extra=1), "unknown key.*extra", id="unknown-key"),
    *[pytest.param(without(key), f"missing key.*{key}", id=f"missing-{key}") for key in VALID],
    pytest.param(text(schema="actuarii-config/2"), "schema", id="schema-other"),
    pytest.param(text(schema=1), "schema", id="schema-not-a-string"),
    pytest.param(text(governed_paths="src/**"), "governed_paths", id="paths-a-string"),
    pytest.param(text(governed_paths={}), "governed_paths", id="paths-an-object"),
    pytest.param(text(governed_paths=[]), "governed_paths", id="paths-empty"),
    pytest.param(text(governed_paths=[1]), "governed_paths", id="paths-not-strings"),
    pytest.param(text(governed_paths=[""]), "governed_paths", id="paths-empty-string"),
    pytest.param(text(governed_paths=["a", "a"]), "duplicate", id="paths-duplicate"),
    pytest.param(text(governed_paths=["/etc/x"]), "absolute", id="paths-absolute"),
    pytest.param(text(governed_paths=["a/../b"]), r"\.\.", id="paths-parent"),
    pytest.param(text(governed_paths=["a\\b"]), "backslash", id="paths-backslash"),
    pytest.param(text(governed_paths=["a?b"]), "wildcard", id="paths-question-mark"),
    pytest.param(text(governed_paths=["a[b]"]), "wildcard", id="paths-class"),
    pytest.param(text(governed_paths=["a{b}"]), "wildcard", id="paths-braces"),
    pytest.param(text(governed_paths=["***"]), "wildcard", id="paths-three-stars"),
    pytest.param(text(python_script_dirs="scripts"), "python_script_dirs", id="dirs-a-string"),
    pytest.param(text(python_script_dirs={}), "python_script_dirs", id="dirs-an-object"),
    pytest.param(text(python_script_dirs=None), "python_script_dirs", id="dirs-null"),
    pytest.param(text(python_script_dirs=[1]), "python_script_dirs", id="dirs-not-strings"),
    pytest.param(text(python_script_dirs=[""]), "python_script_dirs", id="dirs-empty-string"),
    pytest.param(text(python_script_dirs=["a", "a"]), "duplicate", id="dirs-duplicate"),
    pytest.param(text(python_script_dirs=[".", "."]), "duplicate", id="dirs-duplicate-root"),
    pytest.param(text(python_script_dirs=["/etc"]), "absolute", id="dirs-absolute"),
    pytest.param(text(python_script_dirs=["a/"]), "trailing", id="dirs-trailing-slash"),
    pytest.param(text(python_script_dirs=["a/../b"]), r"\.\.", id="dirs-parent"),
    pytest.param(text(python_script_dirs=[".."]), r"\.\.", id="dirs-parent-alone"),
    pytest.param(text(python_script_dirs=["a\\b"]), "backslash", id="dirs-backslash"),
    pytest.param(text(python_script_dirs=["a*"]), "wildcard", id="dirs-star"),
    pytest.param(text(python_script_dirs=["**"]), "wildcard", id="dirs-double-star"),
    pytest.param(text(python_script_dirs=["a?b"]), "wildcard", id="dirs-question-mark"),
    pytest.param(text(python_script_dirs=["a[b]"]), "wildcard", id="dirs-class"),
    pytest.param(text(python_script_dirs=["a{b}"]), "wildcard", id="dirs-braces"),
    pytest.param(text(python_script_dirs=["a\nb"]), "control", id="dirs-newline"),
    pytest.param(text(python_script_dirs=["a\tb"]), "control", id="dirs-tab"),
    pytest.param(text(python_script_dirs=["a\x7fb"]), "control", id="dirs-delete"),
    pytest.param(text(python_script_dirs=["./a"]), "segment", id="dirs-dot-segment"),
    pytest.param(text(python_script_dirs=["a//b"]), "segment", id="dirs-empty-segment"),
    pytest.param(text(contract_registry=1), "contract_registry", id="registry-a-number"),
    pytest.param(text(contract_registry=True), "contract_registry", id="registry-true"),
    pytest.param(text(contract_registry=[]), "contract_registry", id="registry-a-list"),
    pytest.param(text(contract_registry={}), "contract_registry", id="registry-an-object"),
    pytest.param(text(contract_registry=""), "contract_registry", id="registry-empty-string"),
    pytest.param(text(contract_registry="/etc/r.json"), "absolute", id="registry-absolute"),
    pytest.param(text(contract_registry="a/r.json/"), "trailing", id="registry-trailing-slash"),
    pytest.param(text(contract_registry="a/../r.json"), r"\.\.", id="registry-parent"),
    pytest.param(text(contract_registry=".."), r"\.\.", id="registry-parent-alone"),
    pytest.param(text(contract_registry="a\\r.json"), "backslash", id="registry-backslash"),
    pytest.param(text(contract_registry="a/*.json"), "wildcard", id="registry-star"),
    pytest.param(text(contract_registry="**"), "wildcard", id="registry-double-star"),
    pytest.param(text(contract_registry="a?.json"), "wildcard", id="registry-question-mark"),
    pytest.param(text(contract_registry="a[b].json"), "wildcard", id="registry-class"),
    pytest.param(text(contract_registry="a{b}.json"), "wildcard", id="registry-braces"),
    pytest.param(text(contract_registry="a\nb.json"), "control", id="registry-newline"),
    pytest.param(text(contract_registry="a\tb.json"), "control", id="registry-tab"),
    pytest.param(text(contract_registry="a\x7fb.json"), "control", id="registry-delete"),
    pytest.param(text(contract_registry="./r.json"), "segment", id="registry-dot-segment"),
    pytest.param(text(contract_registry="."), "segment", id="registry-dot-alone"),
    pytest.param(text(contract_registry="a//r.json"), "segment", id="registry-empty-segment"),
    pytest.param(text(receipt_window_seconds="60"), "receipt_window_seconds", id="window-a-string"),
    pytest.param(text(receipt_window_seconds=60.5), "receipt_window_seconds", id="window-a-float"),
    pytest.param(text(receipt_window_seconds=True), "receipt_window_seconds", id="window-true"),
    pytest.param(text(receipt_window_seconds=False), "receipt_window_seconds", id="window-false"),
    pytest.param(text(receipt_window_seconds=None), "receipt_window_seconds", id="window-null"),
    pytest.param(text(receipt_window_seconds=0), "receipt_window_seconds", id="window-zero"),
    pytest.param(text(receipt_window_seconds=-1), "receipt_window_seconds", id="window-negative"),
    pytest.param(text(receipt_window_seconds=86401), "receipt_window_seconds", id="window-too-long"),
]


@pytest.mark.parametrize("content, fragment", INVALID)
def test_an_invalid_configuration_is_an_error_naming_its_cause(config_file, content, fragment):
    config_file(content)
    with pytest.raises(ConfigError, match=fragment) as caught:
        load()
    assert ".actuarii.json" in str(caught.value)


def test_a_file_that_is_not_utf_8_is_an_error(config_file):
    config_file(text())
    project_config.CONFIG_PATH.write_bytes(b"\xff\xfe{}")
    with pytest.raises(ConfigError, match="UTF-8"):
        load()


def test_a_configuration_path_that_cannot_be_read_is_an_error(config_file):
    project_config.CONFIG_PATH.mkdir()
    with pytest.raises(ConfigError, match="cannot read"):
        load()


def test_a_valid_configuration_is_loaded_as_written(config_file):
    config_file(VALID)
    config = load()
    assert config.governed_paths == ("src/**", "docs/*.md")
    assert config.python_script_dirs == ("scripts", "tools/sub", ".")
    assert config.contract_registry == "contracts/registry.json"
    assert config.receipt_window_seconds == 60
    assert config.source == ".actuarii.json"


def test_the_contract_registry_may_be_null_and_then_there_is_none(config_file):
    config_file(text(contract_registry=None))
    assert load().contract_registry is None


@pytest.mark.parametrize("registry", ["r.json", "a/b/registry.json", "dir.d/r"])
def test_the_contract_registry_is_a_plain_relative_path(config_file, registry):
    config_file(text(contract_registry=registry))
    assert load().contract_registry == registry


def test_the_script_directories_may_be_an_empty_list(config_file):
    config_file(text(python_script_dirs=[]))
    assert load().python_script_dirs == ()


@pytest.mark.parametrize("seconds", [1, 86400])
def test_the_window_accepts_its_limits(config_file, seconds):
    config_file(text(receipt_window_seconds=seconds))
    assert load().receipt_window_seconds == seconds


# T2: no file

def test_without_a_file_the_built_in_minimum_is_governed_and_says_so(config_file):
    config = load()
    assert config.governed_paths == (".actuarii.json", "AGENTS.md", "CLAUDE.md")
    assert config.python_script_dirs == (".",)
    assert config.contract_registry is None
    assert config.receipt_window_seconds == 900
    assert config.source == BUILT_IN


@pytest.mark.parametrize("rel", ["AGENTS.md", "CLAUDE.md"])
def test_without_a_file_the_minimum_governs_its_paths_and_reports_the_source(config_file, rel):
    verdict = governance(rel)
    assert verdict.source == BUILT_IN
    assert verdict.window_seconds == 900
    assert f'"{rel}"' in verdict.rule


@pytest.mark.parametrize("rel", ["src/a.py", "tests/x.py", "README.md"])
def test_without_a_file_nothing_else_is_governed(config_file, rel):
    assert governance(rel) is None


# the rule behind a verdict

@pytest.mark.parametrize("pattern, rel, governed", [
    ("src/**", "src/a.py", True),
    ("src/**", "src/a/b/c.py", True),
    ("src/**", "src", False),
    ("src/**", "srcx/a.py", False),
    ("docs/*.md", "docs/a.md", True),
    ("docs/*.md", "docs/sub/a.md", False),
    ("docs/*.md", "docs/a.txt", False),
    ("AGENTS.md", "AGENTS.md", True),
    ("AGENTS.md", "agents.md", False),
    ("a.b", "a.b", True),
    ("a.b", "aXb", False),
    ("**/x.py", "x.py", True),
    ("**/x.py", "a/b/x.py", True),
    ("tests/**/*.py", "tests/a.py", True),
    ("tests/**/*.py", "tests/a/b.py", True),
    ("tests/**/*.py", "tests/a/b.txt", False),
])
def test_a_pattern_stays_inside_a_segment_with_star_and_crosses_with_double_star(
        config_file, pattern, rel, governed):
    config_file(text(governed_paths=[pattern]))
    assert (governance(rel) is not None) is governed


def test_a_governed_path_reports_the_pattern_the_source_and_the_window(config_file):
    config_file(VALID)
    verdict = governance("src/a.py")
    assert '"src/**"' in verdict.rule
    assert verdict.source == ".actuarii.json"
    assert verdict.window_seconds == 60


def test_the_first_pattern_that_matches_is_the_rule(config_file):
    config_file(text(governed_paths=["docs/*.md", "docs/**"]))
    assert '"docs/*.md"' in governance("docs/a.md").rule
    assert '"docs/**"' in governance("docs/sub/a.md").rule


@pytest.mark.parametrize("listed", [["src/**"], [".actuarii.json", "src/**"]])
def test_the_configuration_itself_is_always_governed(config_file, listed):
    config_file(text(governed_paths=listed))
    verdict = governance(".actuarii.json")
    assert verdict.rule == OWN_RULE
    assert verdict.source == ".actuarii.json"
    assert verdict.window_seconds == 60


def test_the_configuration_itself_is_governed_when_it_is_invalid_with_the_default_window(config_file):
    config_file("{")
    verdict = governance(".actuarii.json")
    assert verdict.rule == OWN_RULE
    assert verdict.source == ".actuarii.json"
    assert verdict.window_seconds == 900


def test_any_other_path_raises_when_the_configuration_is_invalid(config_file):
    config_file("{")
    with pytest.raises(ConfigError, match="not valid JSON"):
        governance("src/a.py")


# the contract registry is always governed

@pytest.mark.parametrize("listed", [["src/**"], ["contracts/registry.json", "src/**"], ["contracts/**"]])
def test_the_configured_registry_is_always_governed_whether_or_not_it_is_listed(config_file, listed):
    config_file(text(governed_paths=listed))
    verdict = governance("contracts/registry.json")
    assert verdict.rule == REGISTRY_RULE
    assert verdict.source == ".actuarii.json"
    assert verdict.window_seconds == 60


def test_without_a_registry_the_path_that_would_hold_one_is_not_governed(config_file):
    config_file(text(contract_registry=None))
    assert governance("contracts/registry.json") is None


def test_only_the_configured_registry_path_is_governed_as_the_registry(config_file):
    config_file(text())
    assert governance("contracts/other.json") is None
    assert governance("contracts/registry.json.bak") is None


def test_the_registry_is_not_governed_by_the_built_in_minimum(config_file):
    assert governance("contracts/registry.json") is None


def test_the_registry_path_raises_when_the_configuration_is_invalid(config_file):
    config_file("{")
    with pytest.raises(ConfigError, match="not valid JSON"):
        governance("contracts/registry.json")


# the real file of this repository

def test_the_location_is_the_file_at_the_repository_root_and_not_the_environment():
    assert project_config.CONFIG_PATH == ROOT / ".actuarii.json"


def test_the_real_configuration_loads_and_governs_what_this_repository_governs():
    config = load()
    assert config.source == ".actuarii.json"
    assert config.receipt_window_seconds == 900
    assert config.python_script_dirs == ()
    assert config.contract_registry is None
    governed = [
        "AGENTS.md", "CLAUDE.md", "tests/x.py", "tools/boundary_validator/x.py", ".actuarii.json",
        "tools/hooks/x.py", "tools/hooks/sub/y.json", "tools/bin/python3", "tools/bin/python",
    ]
    for rel in governed:
        assert governance(rel) is not None, rel
    assert governance("docs/x.md") is None


# the command line: the shim asks for the directories where Python may run

def kit(tmp_path, content=None):
    """A temporary repository holding a copy of the module, as the shim finds it next to itself."""
    (tmp_path / "tools").mkdir()
    shutil.copy2(SOURCE, tmp_path / "tools" / "project_config.py")
    if content is not None:
        (tmp_path / ".actuarii.json").write_text(
            content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return tmp_path / "tools" / "project_config.py"


def ask(script, *arguments):
    return run([sys.executable, "-I", str(script), *arguments])


def test_the_command_line_prints_one_effective_entry_per_line(tmp_path):
    done = ask(kit(tmp_path, VALID), "--python-script-dirs")
    assert (done.returncode, done.stdout, done.stderr) == (0, "scripts\ntools/sub\n.\n", "")


def test_the_command_line_prints_nothing_for_an_empty_list(tmp_path):
    done = ask(kit(tmp_path, text(python_script_dirs=[])), "--python-script-dirs")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_the_command_line_without_a_file_prints_the_built_in_minimum(tmp_path):
    done = ask(kit(tmp_path), "--python-script-dirs")
    assert (done.returncode, done.stdout, done.stderr) == (0, ".\n", "")


def test_the_command_line_with_an_invalid_file_exits_1_with_the_error_on_stderr(tmp_path):
    done = ask(kit(tmp_path, text(python_script_dirs=["a/../b"])), "--python-script-dirs")
    assert done.returncode == 1 and done.stdout == ""
    assert ".actuarii.json" in done.stderr and "python_script_dirs" in done.stderr


@pytest.mark.parametrize("arguments", [[], ["--other"], ["--python-script-dirs", "x"], ["x", "--python-script-dirs"]])
def test_any_other_command_line_is_a_usage_error_with_exit_2(tmp_path, arguments):
    done = ask(kit(tmp_path, VALID), *arguments)
    assert done.returncode == 2 and done.stdout == "" and done.stderr.strip()


def test_project_config_postpones_annotations_and_parses_as_python_3_9():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), feature_version=(3, 9))
    assert any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in tree.body)
