"""The primitives of a Python source, and the ones a change introduces (tools/boundary_validator/primitives.py).

A primitive is found in the syntax tree, never in the text: an import of a network, process or code-loading
module, a process function of `os`, or a reference to `__import__`, `eval`, `exec` or `compile`. The sources
the tests probe are string literals: nothing here imports a primitive.
"""
import pytest

from tools.boundary_validator.primitives import NotPython, introduced, primitives

ROOTS = [
    "subprocess", "socket", "urllib", "http", "ftplib", "telnetlib", "xmlrpc", "webbrowser", "importlib",
    "ctypes", "pty", "requests", "httpx", "aiohttp", "urllib3", "posix", "nt", "_posixsubprocess", "_socket",
    "multiprocessing", "asyncio",
]
OS_FUNCTIONS = [
    "system", "popen", "fork", "forkpty", "execv", "execl", "execvp", "execle", "spawnl", "spawnvp",
    "posix_spawn", "posix_spawnp",
]
BARE_NAMES = ["__import__", "eval", "exec", "compile"]


# T1: every kind of primitive is found


@pytest.mark.parametrize("root", ROOTS)
@pytest.mark.parametrize("form", [
    "import {root}",
    "import {root}.sub",
    "import {root} as x",
    "import {root}.sub as x",
    "import os, {root}",
    "from {root} import name",
    "from {root}.sub import name",
    "from {root} import name as other",
    "if True:\n    import {root}",
    "def f():\n    from {root} import name",
])
def test_an_import_of_a_listed_module_is_a_primitive(root, form):
    assert primitives(form.format(root=root)) == {f"import {root}"}


@pytest.mark.parametrize("name", OS_FUNCTIONS)
def test_an_os_function_read_on_os_is_a_primitive(name):
    assert primitives(f"import os\nos.{name}('x')") == {f"os.{name}"}
    assert primitives(f"os.{name}('x')") == {f"os.{name}"}
    assert primitives(f"import os\nf = os.{name}") == {f"os.{name}"}


@pytest.mark.parametrize("name", OS_FUNCTIONS)
def test_an_os_function_read_on_an_alias_of_os_is_the_same_primitive(name):
    assert primitives(f"import os as o\no.{name}('x')") == {f"os.{name}"}
    assert primitives(f"import sys, os as _o\nvalue = _o.{name}") == {f"os.{name}"}


@pytest.mark.parametrize("name", OS_FUNCTIONS)
def test_an_os_function_imported_from_os_is_the_same_primitive(name):
    assert primitives(f"from os import {name}") == {f"os.{name}"}
    assert primitives(f"from os import path, {name} as run") == {f"os.{name}"}


def test_a_star_import_from_os_is_a_primitive_named_os_star():
    assert primitives("from os import *") == {"os.*"}
    assert primitives("from os import *\nfrom os import system") == {"os.*", "os.system"}
    assert primitives("def f():\n    from os import *") == {"os.*"}


def test_a_star_import_from_anything_but_os_is_not_the_os_primitive():
    assert primitives("from os.path import *") == set()
    assert primitives("from .os import *") == set()
    assert primitives("from subprocess import *") == {"import subprocess"}


@pytest.mark.parametrize("name", BARE_NAMES)
def test_a_reference_to_a_loader_name_is_a_primitive_even_without_a_call(name):
    assert primitives(f"{name}('x')") == {name}
    assert primitives(f"f = {name}") == {name}
    assert primitives(f"items = [{name}]") == {name}
    assert primitives(f"def f():\n    return {name}") == {name}


def test_a_source_with_several_primitives_names_each_once():
    source = "import subprocess\nimport subprocess as sp\nimport os\nos.system('x')\nos.system('y')\neval('1')\n"
    assert primitives(source) == {"import subprocess", "os.system", "eval"}


# T2: what looks like a primitive and is not


@pytest.mark.parametrize("source", [
    "x = 'import subprocess'",
    "x = \"os.system('id')\"",
    "x = '''\nimport socket\neval(1)\n'''",
    "# import subprocess\nvalue = 1",
    "def f():\n    '''import socket'''\n",
    "import re\nre.compile('x')",
    "pattern.compile('x')",
    "x.eval('1')",
    "runner.exec('1')",
    "x.system('id')",
    "from . import subprocess",
    "from .subprocess import run",
    "from .. import socket",
    "from ..requests import get",
    "import subprocessx",
    "import socketserver",
    "import urllib_extra",
    "import httpx_extra",
    "import requests_toolbelt",
    "import os\nos.path.join('a', 'b')\nos.getcwd()\nos.environ",
    "from os import path, getcwd, environ",
    "from os.path import join",
    "import os.path",
    "import os as o\no.getcwd()",
    "import os\nos.systematic",
    "import os\nos.forks",
    "evaluate('x')",
    "compiler = 1",
    "exec = 1",
    "def f(eval):\n    return 1",
    "class K:\n    compile = 1",
    "",
    "x = 1",
])
def test_what_is_not_a_primitive_is_not_found(source):
    assert primitives(source) == set(), source


# T3: only what the change introduces


def test_a_second_use_of_a_primitive_the_file_already_has_is_not_new():
    before = "import subprocess\nsubprocess.run(['id'])\n"
    after = before + "subprocess.run(['ls'])\nimport subprocess as sp\nfrom subprocess import run\n"
    assert introduced(before, after) == []


def test_a_primitive_the_file_does_not_have_is_new_and_the_ones_it_has_are_not():
    before = "import subprocess\n"
    after = "import subprocess\nimport socket\n"
    assert introduced(before, after) == ["import socket"]


def test_the_new_primitives_are_sorted_and_named_by_kind_and_target():
    after = "import socket\nimport os\nos.system('x')\neval('1')\nfrom os import popen\n"
    assert introduced("", after) == ["eval", "import socket", "os.popen", "os.system"]


def test_a_primitive_of_another_kind_is_new_even_if_a_similar_one_exists():
    assert introduced("import os\nos.popen('x')\n", "import os\nos.system('x')\n") == ["os.system"]


def test_the_baseline_is_a_set_of_names_so_a_chained_edit_is_new_against_the_file_it_edits():
    assert introduced("import subpbb\n", "import subprocess\n") == ["import subprocess"]


@pytest.mark.parametrize("before", [None, "", "def broken(:\n", "import subprocess(\n", "x = 1\x00\n"])
def test_with_no_usable_source_before_every_primitive_of_the_result_is_new(before):
    assert introduced(before, "import subprocess\nos.system('x')\n") == ["import subprocess", "os.system"]


def test_a_result_that_does_not_parse_is_an_error():
    with pytest.raises(NotPython):
        introduced("x = 1\n", "def broken(:\n")
    with pytest.raises(NotPython):
        introduced(None, "x = 1\x00\n")
    with pytest.raises(NotPython):
        primitives("import (\n")


def test_not_python_is_a_value_error_so_a_caller_that_expects_one_still_denies():
    assert issubclass(NotPython, ValueError)


def test_a_result_that_removes_a_primitive_introduces_nothing():
    assert introduced("import subprocess\nimport socket\n", "import socket\n") == []
