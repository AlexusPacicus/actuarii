"""Python gate (AGENTS 2.5): the PATH shim tools/bin/python3 and the session hook that puts it
first on the PATH of every Bash call. Static properties of the files.

Normative: AGENTS.md 2.5, 6.2
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "tools" / "bin"
SCRIPTS = [BIN / "python3", ROOT / "tools" / "hooks" / "session_python_gate.sh"]


# T12: static properties


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_script_is_an_executable_posix_sh_script(script):
    assert os.access(script, os.X_OK)
    assert script.read_text(encoding="utf-8").startswith("#!/bin/sh\n")


@pytest.mark.parametrize("name", ["python", "python3.11"])
def test_the_other_interpreter_names_are_links_to_the_shim(name):
    assert (BIN / name).is_symlink()
    assert os.readlink(BIN / name) == "python3"
