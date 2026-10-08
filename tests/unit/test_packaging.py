"""The packaging metadata of v0.1.0: pyproject.toml, the Apache-2.0 LICENSE, the NOTICE and the pin the installer reads."""
import hashlib
import tomllib
from pathlib import Path

from tools import install

ROOT = Path(__file__).resolve().parents[2]
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
LICENSE_SIZE = 11358
NOTICE_HEAD = ["Actuarii", "Copyright 2026 Alexis Zapico Fernández"]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_project_table_carries_the_v010_metadata():
    assert list(PYPROJECT["project"]) == [
        "name",
        "version",
        "description",
        "license",
        "license-files",
        "authors",
        "requires-python",
        "dependencies",
        "optional-dependencies",
    ]
    project = PYPROJECT["project"]
    assert project["name"] == "actuarii"
    assert project["version"] == "0.1.0"
    assert project["description"] == (
        "Governance kit for coding agents: rules enforced in code, with receipts, for Claude Code."
    )
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    assert all((ROOT / name).is_file() for name in project["license-files"])
    assert project["authors"] == [{"name": "Alexis Zapico Fernández"}]
    assert project["requires-python"] == "~=3.11"
    assert project["dependencies"] == ["pydantic==2.13.3"]
    assert project["optional-dependencies"] == {"dev": ["pytest>=8.0.0"]}


def test_no_build_system_and_pytest_options_unchanged():
    assert set(PYPROJECT) == {"project", "tool"}
    assert PYPROJECT["tool"] == {"pytest": {"ini_options": {"testpaths": ["tests"], "addopts": ["--strict-markers"]}}}


def test_license_is_the_official_apache_text_and_notice_names_the_holder():
    text = (ROOT / "LICENSE").read_bytes()
    assert len(text) == LICENSE_SIZE
    assert hashlib.sha256(text).hexdigest() == LICENSE_SHA256
    assert (ROOT / "NOTICE").read_text(encoding="utf-8").splitlines()[:2] == NOTICE_HEAD


def test_installer_pin_is_the_pydantic_dependency_of_pyproject():
    (dependency,) = PYPROJECT["project"]["dependencies"]
    assert dependency == "pydantic==" + install.pydantic_pin()
