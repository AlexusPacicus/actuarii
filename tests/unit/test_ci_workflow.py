"""The CI workflow of phase 2, read as text: no YAML library, so no new dependency."""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
INSTALLER_TESTS = ROOT / "tests" / "unit" / "test_installer.py"
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

HEADER = """name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
"""
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"
SETUP_PYTHON = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0"
PYTEST_PIN = "pytest==9.1.1"
CLEAN_ROOM_NAME = "Clean-room sequence (docs/design/PRUEBA_EN_LIMPIO.md, section 4)"
CLEAN_ROOM_TESTS = [
    "test_a_fresh_install_copies_every_kit_file_with_its_bytes_and_executable_bit",
    "test_before_the_validator_has_ever_run_the_installed_gate_still_denies",
    "test_the_installed_kit_denies_an_unreceipted_write_and_allows_it_after_the_targets_own_receipt",
    "test_the_installed_kit_is_committed_with_its_own_hook_and_head_holds_the_shim_names_as_equal_executables",
]
FIELD = r"(?m)^\s+(name|uses|run|persist-credentials|python-version): (.+)$"


def workflow_text():
    assert WORKFLOW.is_file(), f"{WORKFLOW.relative_to(ROOT)} does not exist"
    return WORKFLOW.read_text(encoding="utf-8")


def steps():
    text = workflow_text()
    assert text.startswith(HEADER), "the workflow does not start with the decided header"
    chunks = re.split(r"(?m)^      - ", text[len(HEADER):])
    assert chunks[0] == "", "something precedes the first step"
    return [dict(re.findall(FIELD, "        " + chunk)) for chunk in chunks[1:]]


def test_the_workflow_runs_on_push_to_main_pull_requests_and_by_hand_read_only_on_a_pinned_runner():
    text = workflow_text()
    assert text.startswith(HEADER)
    assert text.count("steps:") == 1
    assert "secrets" not in text.lower()
    assert ": write" not in text
    assert "write-all" not in text
    assert "pull_request_target" not in text
    assert text.endswith("\n")


def test_it_uses_only_checkout_and_setup_python_pinned_by_sha_with_credentials_not_persisted_on_python_311():
    text = workflow_text()
    assert text.count("uses:") == 2
    found = steps()
    assert [step.get("uses") for step in found[:2]] == [CHECKOUT, SETUP_PYTHON]
    assert found[0].get("persist-credentials") == "false"
    assert found[1].get("python-version") == '"3.11"'
    assert all("uses" not in step for step in found[2:])
    assert text.count("persist-credentials:") == 1
    assert text.count("python-version:") == 1


def test_it_installs_exactly_the_pyproject_pydantic_pin_and_the_pinned_pytest():
    pins = [name for name in PYPROJECT["project"]["dependencies"] if name.startswith("pydantic")]
    assert len(pins) == 1
    text = workflow_text()
    installs = [step for step in steps() if "pip" in step.get("run", "")]
    assert len(installs) == 1
    assert installs[0]["run"] == f"pip install {pins[0]} {PYTEST_PIN}"
    assert text.count("pip") == 1
    assert "pip install ." not in text


def test_the_clean_room_sequence_runs_its_own_step_then_the_full_suite_with_pytest_deciding_each_exit_status():
    installer_tests = INSTALLER_TESTS.read_text(encoding="utf-8")
    for name in CLEAN_ROOM_TESTS:
        assert f"\ndef {name}(" in installer_tests, f"{name} is not a test of tests/unit/test_installer.py"
    found = steps()
    assert [step.get("name") for step in found[2:]] == [
        "Install dependencies",
        CLEAN_ROOM_NAME,
        "Full suite",
    ]
    clean_room, full = found[3]["run"], found[4]["run"]
    assert clean_room == "pytest " + " ".join(f"tests/unit/test_installer.py::{name}" for name in CLEAN_ROOM_TESTS)
    assert full == "pytest tests"
    for command in (clean_room, full):
        assert not set(command) & set("|;&<>`$()"), command
