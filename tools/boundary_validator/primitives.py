"""The primitives of a Python source: what a write must not introduce into a governed file.

A primitive is found in the syntax tree, never in the text, so a string, a comment or `re.compile` is not one:

* an absolute import (`import M`, `import M.N as X`, `from M[.N] import ...`) whose root module is in
  IMPORT_ROOTS, named `import <root>`;
* an `os` process function (`system`, `popen`, `fork`, `forkpty`, or a name starting with `exec`, `spawn` or
  `posix_spawn`) imported from `os` or read as an attribute of `os` or of a name bound by `import os as X`,
  named `os.<function>`; `from os import *` is one as well, named `os.*`;
* a read of the bare name `__import__`, `eval`, `exec` or `compile` (a reference is enough, not only a call),
  named after itself.

The write gate (tools/hooks/require_boundary_validation.py) and the validator share this module. It imports only
the standard library and postpones annotations because the gate runs under a system Python that may be 3.9, and
a gate that cannot import it denies.
"""
from __future__ import annotations

import ast
from typing import Optional

IMPORT_ROOTS = frozenset({
    "subprocess", "socket", "urllib", "http", "ftplib", "telnetlib", "xmlrpc", "webbrowser", "importlib",
    "ctypes", "pty", "requests", "httpx", "aiohttp", "urllib3", "posix", "nt", "_posixsubprocess", "_socket",
    "multiprocessing", "asyncio",
})
OS_FUNCTIONS = frozenset({"system", "popen", "fork", "forkpty"})
OS_FUNCTION_PREFIXES = ("exec", "spawn", "posix_spawn")
LOADER_NAMES = frozenset({"__import__", "eval", "exec", "compile"})


class NotPython(ValueError):
    """A source that `ast` cannot parse; callers deny it, they never read it as free of primitives."""


def _parse(source: str) -> ast.AST:
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise NotPython(str(exc)) from exc


def _is_os_function(name: str) -> bool:
    return name in OS_FUNCTIONS or name.startswith(OS_FUNCTION_PREFIXES)


def primitives(source: str) -> set[str]:
    """The names of the primitives of `source`, one per kind and target; raises NotPython when it does not parse."""
    nodes = list(ast.walk(_parse(source)))
    os_names = {"os"}
    for node in nodes:
        if isinstance(node, ast.Import):
            os_names.update(alias.asname for alias in node.names if alias.name == "os" and alias.asname)
    found: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in IMPORT_ROOTS:
                    found.add(f"import {root}")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            root = node.module.split(".")[0]
            if root in IMPORT_ROOTS:
                found.add(f"import {root}")
            if node.module == "os":
                found.update(f"os.{alias.name}" for alias in node.names
                              if alias.name == "*" or _is_os_function(alias.name))
        elif isinstance(node, ast.Attribute):
            if (isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name)
                    and node.value.id in os_names and _is_os_function(node.attr)):
                found.add(f"os.{node.attr}")
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load) and node.id in LOADER_NAMES:
                found.add(node.id)
    return found


def introduced(before: Optional[str], after: str) -> list[str]:
    """The primitives of `after` that `before` does not have, sorted; raises NotPython when `after` does not parse.

    A `before` that is None or does not parse gives the empty baseline: the whole of `after` is checked.
    """
    result = primitives(after)
    if before is None:
        return sorted(result)
    try:
        baseline = primitives(before)
    except NotPython:
        baseline = set()
    return sorted(result - baseline)
