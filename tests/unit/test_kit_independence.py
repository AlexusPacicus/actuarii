import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {"traianus", "fastapi", "numpy", "helpers"}
MODULES = sorted(path for tree in ("tests", "tools") for path in (ROOT / tree).rglob("*.py"))


def _imported_roots(path: Path) -> set:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module", MODULES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_module_imports_the_engine_or_its_dependencies(module):
    assert _imported_roots(module) & FORBIDDEN == set()
