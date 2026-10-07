"""Sandbox settings (key `sandbox` of .claude/settings.json), docs/design/SANDBOX.md section 6.

The sandbox is what stops Bash from reaching the network and from writing the governed paths, so its
values are pinned: a loosened value, an extra key, a missing denyWrite entry or an extra one is red.
The link with .actuarii.json is computed from the configuration it reads, not from a copied list.
"""

import copy
import json
from pathlib import Path

import pytest

from tools.boundary_validator import hook_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
CONFIG = REPO_ROOT / ".actuarii.json"

SELF_PROTECTED = (".claude/**", ".mcp.json")
STRICT = {
    "enabled": True,
    "failIfUnavailable": True,
    "allowUnsandboxedCommands": False,
    "autoAllowBashIfSandboxed": False,
}
SANDBOX_KEYS = set(STRICT) | {"filesystem"}
AUDIT_DB = "./" + hook_gate.DEFAULT_AUDIT_DB.relative_to(REPO_ROOT).as_posix()
CONFIG_ENTRY = "./" + CONFIG.name


def deny_entry(governed_path):
    return "./" + governed_path.removesuffix("/**")


def expected_deny_write(config):
    """The paths of the configuration, the configuration file and the registry (always governed) and the
    audit database; `.claude/**` and `.mcp.json` are protected by the sandbox itself."""
    governed = [path for path in config["governed_paths"] if path not in SELF_PROTECTED]
    if config["contract_registry"] is not None:
        governed.append(config["contract_registry"])
    return sorted({deny_entry(path) for path in governed} | {CONFIG_ENTRY, AUDIT_DB})


def sandbox_problems(settings, config):
    sandbox = settings.get("sandbox")
    if not isinstance(sandbox, dict):
        return ["no sandbox object"]
    problems = [
        f"sandbox.{key} is not {value}" for key, value in STRICT.items() if sandbox.get(key) is not value
    ]
    if set(sandbox) != SANDBOX_KEYS:
        problems.append(f"sandbox keys are {sorted(sandbox)}")
    filesystem = sandbox.get("filesystem")
    if not isinstance(filesystem, dict):
        return problems + ["no sandbox.filesystem object"]
    if set(filesystem) != {"denyWrite"}:
        problems.append(f"sandbox.filesystem keys are {sorted(filesystem)}")
    deny_write = filesystem.get("denyWrite")
    if not isinstance(deny_write, list) or sorted(deny_write) != expected_deny_write(config):
        problems.append(f"denyWrite is {deny_write}, expected {expected_deny_write(config)}")
    return problems


def committed_settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def committed_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def config_with(**changes):
    return {**committed_config(), **changes}


def mutated(change):
    settings = copy.deepcopy(committed_settings())
    change(settings["sandbox"])
    return settings


def test_the_committed_sandbox_settings_have_no_problem():
    assert sandbox_problems(committed_settings(), committed_config()) == []


def test_the_committed_sandbox_values_are_strict():
    sandbox = committed_settings()["sandbox"]
    assert {key: sandbox[key] for key in STRICT} == STRICT
    assert "excludedCommands" not in sandbox
    assert "allowWrite" not in sandbox["filesystem"]
    assert "disabled" not in sandbox["filesystem"]
    assert set(sandbox) == SANDBOX_KEYS
    assert set(sandbox["filesystem"]) == {"denyWrite"}


def test_the_committed_deny_write_holds_the_audit_database_and_nothing_unexplained():
    deny_write = committed_settings()["sandbox"]["filesystem"]["denyWrite"]
    assert AUDIT_DB == "./.data/boundary_validator_audit.db"
    assert AUDIT_DB in deny_write
    assert sorted(deny_write) == expected_deny_write(committed_config())


@pytest.mark.parametrize("key, loosened", [
    ("enabled", False),
    ("failIfUnavailable", False),
    ("allowUnsandboxedCommands", True),
    ("autoAllowBashIfSandboxed", True),
])
def test_a_strict_value_turned_the_other_way_is_a_problem(key, loosened):
    settings = mutated(lambda sandbox: sandbox.__setitem__(key, loosened))
    assert sandbox_problems(settings, committed_config()) == [f"sandbox.{key} is not {STRICT[key]}"]


@pytest.mark.parametrize("key", sorted(STRICT))
def test_a_strict_key_that_is_missing_is_a_problem(key):
    settings = mutated(lambda sandbox: sandbox.pop(key))
    assert sandbox_problems(settings, committed_config())


def test_a_missing_or_malformed_sandbox_is_a_problem():
    settings = committed_settings()
    del settings["sandbox"]
    assert sandbox_problems(settings, committed_config()) == ["no sandbox object"]
    settings["sandbox"] = True
    assert sandbox_problems(settings, committed_config()) == ["no sandbox object"]


@pytest.mark.parametrize("change", [
    lambda sandbox: sandbox.__setitem__("excludedCommands", ["git"]),
    lambda sandbox: sandbox.__setitem__("excludedCommands", []),
    lambda sandbox: sandbox["filesystem"].__setitem__("allowWrite", ["./tests"]),
    lambda sandbox: sandbox["filesystem"].__setitem__("allowWrite", []),
    lambda sandbox: sandbox["filesystem"].__setitem__("disabled", True),
    lambda sandbox: sandbox["filesystem"].__setitem__("disabled", False),
    lambda sandbox: sandbox.__setitem__("network", {}),
    lambda sandbox: sandbox["filesystem"].__setitem__("denyRead", []),
], ids=["excludedCommands", "excludedCommands-empty", "allowWrite", "allowWrite-empty",
        "disabled-true", "disabled-false", "extra-sandbox-key", "extra-filesystem-key"])
def test_a_key_beyond_the_pinned_ones_is_a_problem(change):
    assert sandbox_problems(mutated(change), committed_config())


def test_a_dropped_deny_write_entry_is_a_problem():
    for entry in committed_settings()["sandbox"]["filesystem"]["denyWrite"]:
        settings = mutated(lambda sandbox: sandbox["filesystem"]["denyWrite"].remove(entry))
        assert sandbox_problems(settings, committed_config()), entry


def test_an_extra_deny_write_entry_is_a_problem():
    settings = mutated(lambda sandbox: sandbox["filesystem"]["denyWrite"].append("./docs"))
    assert sandbox_problems(settings, committed_config())


def test_a_duplicated_deny_write_entry_is_a_problem():
    settings = mutated(lambda sandbox: sandbox["filesystem"]["denyWrite"].append(AUDIT_DB))
    assert sandbox_problems(settings, committed_config())


def test_a_governed_path_added_to_the_configuration_needs_its_deny_write_entry():
    config = config_with(governed_paths=committed_config()["governed_paths"] + ["examples/**", "LICENSE"])
    problems = sandbox_problems(committed_settings(), config)
    assert len(problems) == 1
    assert "./examples" in problems[0] and "./LICENSE" in problems[0]
    settings = mutated(lambda sandbox: sandbox["filesystem"]["denyWrite"].extend(["./examples", "./LICENSE"]))
    assert sandbox_problems(settings, config) == []


def test_a_contract_registry_added_to_the_configuration_needs_its_deny_write_entry():
    config = config_with(contract_registry="contracts/registry.json")
    problems = sandbox_problems(committed_settings(), config)
    assert len(problems) == 1 and "./contracts/registry.json" in problems[0]


def test_a_governed_path_removed_from_the_configuration_leaves_an_unexplained_entry():
    governed = [path for path in committed_config()["governed_paths"] if path != "pyproject.toml"]
    assert sandbox_problems(committed_settings(), config_with(governed_paths=governed))


def test_deny_entries_are_dot_slash_paths_without_the_trailing_glob():
    config = {"governed_paths": ["tests/**", "AGENTS.md", ".claude/**", ".mcp.json", "tools/**"],
              "contract_registry": None}
    assert expected_deny_write(config) == sorted(["./tests", "./AGENTS.md", "./tools", CONFIG_ENTRY, AUDIT_DB])


def test_the_configuration_read_lists_the_two_paths_the_sandbox_protects_by_itself():
    assert all(path in committed_config()["governed_paths"] for path in SELF_PROTECTED)
