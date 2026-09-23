"""Review confinement hook (tools/hooks/confine_review_reads.py, AGENTS 6.1).

While a review lock names a package directory, Read, Grep and Glob may only reach paths inside
it; without a lock the hook is inert. Blindness then holds by construction, not by instruction.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

from tools.hooks.confine_review_reads import decide, main

HOOK = Path(__file__).resolve().parents[2] / "tools" / "hooks" / "confine_review_reads.py"


def test_hook_imports_only_the_standard_library():
    tree = ast.parse(HOOK.read_text())
    roots = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)


def test_hook_postpones_annotations_for_old_system_interpreters():
    """An import failure exits 1, which the harness reads as a broken hook, not a denial."""
    tree = ast.parse(HOOK.read_text())
    assert any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               and any(a.name == "annotations" for a in n.names) for n in tree.body)


@pytest.fixture
def layout(tmp_path):
    package = tmp_path / "package"
    (package / "frontend" / "audits").mkdir(parents=True)
    (package / "frontend" / "audits" / "K6.md").write_text("record\n")
    repo = tmp_path / "repo"
    (repo / "frontend").mkdir(parents=True)
    (repo / "frontend" / "POC.md").write_text("hypothesis\n")
    lock = tmp_path / "review_lock.json"
    return package, repo, lock


def _lock(lock, package):
    lock.write_text(json.dumps({"package": str(package)}))


def _payload(tool, tool_input, cwd):
    return {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)}


def test_no_lock_allows_everything(layout):
    _package, repo, lock = layout
    allowed, _ = decide(_payload("Read", {"file_path": str(repo / "frontend/POC.md")}, repo), lock)
    assert allowed


def test_read_inside_package_allowed(layout):
    package, repo, lock = layout
    _lock(lock, package)
    target = package / "frontend/audits/K6.md"
    assert decide(_payload("Read", {"file_path": str(target)}, repo), lock)[0]


def test_read_outside_package_denied(layout):
    package, repo, lock = layout
    _lock(lock, package)
    allowed, reason = decide(_payload("Read", {"file_path": str(repo / "frontend/POC.md")}, repo), lock)
    assert not allowed
    assert "outside the review package" in reason


def test_relative_read_resolves_against_cwd(layout):
    package, repo, lock = layout
    _lock(lock, package)
    assert not decide(_payload("Read", {"file_path": "frontend/POC.md"}, repo), lock)[0]
    assert decide(_payload("Read", {"file_path": "frontend/audits/K6.md"}, package), lock)[0]


def test_parent_escape_denied(layout):
    package, repo, lock = layout
    _lock(lock, package)
    escape = str(package / ".." / "repo" / "frontend" / "POC.md")
    assert not decide(_payload("Read", {"file_path": escape}, repo), lock)[0]


def test_symlink_out_of_package_denied(layout):
    package, repo, lock = layout
    _lock(lock, package)
    link = package / "leak.md"
    link.symlink_to(repo / "frontend" / "POC.md")
    assert not decide(_payload("Read", {"file_path": str(link)}, repo), lock)[0]


def test_prefix_sibling_directory_denied(layout, tmp_path):
    package, repo, lock = layout
    _lock(lock, package)
    sibling = tmp_path / "package-other"
    sibling.mkdir()
    (sibling / "x.md").write_text("x\n")
    assert not decide(_payload("Read", {"file_path": str(sibling / "x.md")}, repo), lock)[0]


def test_grep_without_path_uses_cwd(layout):
    package, repo, lock = layout
    _lock(lock, package)
    assert not decide(_payload("Grep", {"pattern": "x"}, repo), lock)[0]
    assert decide(_payload("Grep", {"pattern": "x"}, package), lock)[0]


def test_grep_path_inside_allowed_and_escaping_glob_filter_denied(layout):
    package, repo, lock = layout
    _lock(lock, package)
    assert decide(_payload("Grep", {"pattern": "x", "path": str(package)}, repo), lock)[0]
    assert not decide(
        _payload("Grep", {"pattern": "x", "path": str(package), "glob": "../repo/**"}, repo), lock
    )[0]


def test_glob_patterns(layout):
    package, repo, lock = layout
    _lock(lock, package)
    assert decide(_payload("Glob", {"pattern": "**/*.md", "path": str(package)}, repo), lock)[0]
    assert not decide(_payload("Glob", {"pattern": "**/*.md"}, repo), lock)[0]
    assert not decide(
        _payload("Glob", {"pattern": str(repo / "frontend" / "*.md"), "path": str(package)}, repo),
        lock,
    )[0]
    assert not decide(
        _payload("Glob", {"pattern": "../repo/**/*.md", "path": str(package)}, repo), lock
    )[0]


def test_other_tools_are_not_gated(layout):
    package, repo, lock = layout
    _lock(lock, package)
    assert decide(_payload("Edit", {"file_path": str(repo / "frontend/POC.md")}, repo), lock)[0]


@pytest.mark.parametrize("content", ["not json", json.dumps({"package": "relative/dir"}),
                                     json.dumps({"other": 1})])
def test_corrupt_lock_fails_closed(layout, content):
    package, repo, lock = layout
    lock.write_text(content)
    target = package / "frontend/audits/K6.md"
    assert not decide(_payload("Read", {"file_path": str(target)}, repo), lock)[0]


def test_lock_naming_a_missing_package_fails_closed(layout, tmp_path):
    package, repo, lock = layout
    _lock(lock, tmp_path / "gone")
    assert not decide(_payload("Read", {"file_path": str(package / "x")}, repo), lock)[0]


@pytest.mark.parametrize("tool_input", [{}, {"file_path": ""}, {"file_path": 3}])
def test_malformed_input_fails_closed_under_lock(layout, tool_input):
    package, repo, lock = layout
    _lock(lock, package)
    assert not decide(_payload("Read", tool_input, repo), lock)[0]


def test_main_exit_codes(layout, capsys):
    package, repo, lock = layout
    _lock(lock, package)
    inside = json.dumps(_payload("Read", {"file_path": str(package / "frontend/audits/K6.md")}, repo))
    outside = json.dumps(_payload("Read", {"file_path": str(repo / "frontend/POC.md")}, repo))
    assert main(inside, lock) == 0
    assert main(outside, lock) == 2
    assert "outside the review package" in capsys.readouterr().err
    assert main("{not json", lock) == 2
