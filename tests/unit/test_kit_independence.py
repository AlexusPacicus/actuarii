import ast
import re
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


CLAUSE_CITATION = re.compile("AGENTS" + r"(?:\.md)?\s*(?:§|SS|\d)")
ENGINE_NAME = re.compile("traia" + "nus", re.IGNORECASE)
TOOLS_TEXT = sorted(
    path for path in (ROOT / "tools").rglob("*") if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("path", TOOLS_TEXT, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_tools_file_cites_a_clause_of_the_constitution_or_names_the_engine(path):
    text = _text(path)
    assert CLAUSE_CITATION.search(text) is None
    assert ENGINE_NAME.search(text) is None


@pytest.mark.parametrize("path", [p for p in MODULES if p.is_relative_to(ROOT / "tests")], ids=lambda p: str(p.relative_to(ROOT)))
def test_no_test_file_cites_a_clause_of_the_constitution(path):
    assert CLAUSE_CITATION.search(_text(path)) is None


def test_the_clause_pattern_matches_the_citation_forms():
    name = "AGEN" + "TS"
    forms = [f"{name} 2.1", f"{name}.md 6.2", f"{name}.md §5", f"{name}.md SS6.2", f"{name}\n2.5", f"{name} 6"]
    assert [form for form in forms if CLAUSE_CITATION.search(form) is None] == []
    assert CLAUSE_CITATION.search(f"{name}.md, the constitution") is None


OLD_NAME = "radi" + "cal"
OLD_NAME_EXEMPT = ROOT / "tests" / "security" / "test_rationale.py"


def test_no_tools_or_tests_file_uses_the_old_name_of_the_proposal_fields():
    assert [str(p.relative_to(ROOT)) for p in MODULES if p != OLD_NAME_EXEMPT and OLD_NAME in _text(p).lower()] == []


def test_no_module_docstring_of_tools_or_tests_says_by_construction():
    docstrings = {p: (ast.get_docstring(ast.parse(_text(p))) or "").lower() for p in MODULES}
    assert [str(p.relative_to(ROOT)) for p, doc in docstrings.items() if "by construction" in doc] == []


NUMBERED_PHASE = re.compile(r"\b(phase|fase) \d", re.IGNORECASE)


def test_no_module_docstring_of_tools_or_tests_names_a_numbered_phase():
    docstrings = {p: ast.get_docstring(ast.parse(_text(p))) or "" for p in MODULES}
    assert [str(p.relative_to(ROOT)) for p, doc in docstrings.items() if NUMBERED_PHASE.search(doc)] == []
