"""Both path gates decide by filesystem identity, not by the spelled path (AGENTS.md 6.2).

On a case-insensitive filesystem (APFS by default) `TESTS/x.py` and `tests/x.py` name one file, and a
gate that compares spellings lets the first through. tools/hooks/require_boundary_validation.py and
tools/hooks/require_contract_context.py therefore re-spell the target with the names the filesystem
stores (`canonical`) before they decide. Each hook carries its own copy: the contract hook may import
only the standard library, so it cannot import a sibling module; `test_the_two_copies_are_the_same_code`
keeps them equal.

CI runs on a case-sensitive filesystem, where the bypass cannot happen. The identity primitives are
therefore parameters, and CaseBlindFs answers like APFS over a real tree; the tests that touch the real
filesystem skip, with a reason, where it is case-sensitive.
"""
import ast
import io
import json
import os
import sys
import unicodedata
from pathlib import Path

import pytest

from tools.hooks import require_boundary_validation, require_contract_context
from traianus.security.hook_gate import REPO_ROOT
from traianus.security.validator import validate_proposal

HOOKS = pytest.mark.parametrize(
    "hook", [require_boundary_validation, require_contract_context], ids=["boundary", "contract"])
BOUNDARY_HOOK_FILE = REPO_ROOT / "tools" / "hooks" / "require_boundary_validation.py"
CONTRACT_HOOK_FILE = REPO_ROOT / "tools" / "hooks" / "require_contract_context.py"
SHOUT = str(REPO_ROOT).upper()
SWAP = str(REPO_ROOT).swapcase()
REFUSAL = "denied by the test"


def name_form(name):
    return unicodedata.normalize("NFD", name).casefold()


class CaseBlindFs:
    """The way APFS answers, over any tree: a name matches whatever its case or Unicode form."""

    def real(self, path):
        found = Path(Path(path).anchor)
        for name in Path(path).parts[1:]:
            hits = sorted(n for n in os.listdir(found) if name_form(n) == name_form(name))
            if not hits:
                raise FileNotFoundError(path)
            found = Path(os.path.realpath(found / (name if name in hits else hits[0])))
        return found

    def samefile(self, first, second):
        return self.real(first) == self.real(second)

    def scandir(self, path):
        return os.scandir(self.real(path))


FS = CaseBlindFs()
BLIND = {"samefile": FS.samefile, "scandir": FS.scandir}


def refuse(*_args):
    raise PermissionError(REFUSAL)


@pytest.fixture
def tree(tmp_path):
    root = tmp_path.resolve() / "repo"
    for name in ("src/vec.py", "src/Deep/File.py", "src/Café.py", "tests/x.py", "AGENTS.md"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("", encoding="utf-8")
    (root / "lnk").symlink_to(root / "src", target_is_directory=True)
    (root / "alias.py").symlink_to(root / "src" / "vec.py")
    sibling = root.parent / "repo-other"
    sibling.mkdir()
    (sibling / "x.py").write_text("", encoding="utf-8")
    return root


# T1: the helper on a filesystem that ignores case

INSIDE = [
    ("src/vec.py", "src/vec.py"),
    ("SRC/vec.py", "src/vec.py"),
    ("src/VEC.PY", "src/vec.py"),
    ("src/deep/file.py", "src/Deep/File.py"),
    ("SRC/DEEP/FILE.PY", "src/Deep/File.py"),
    ("SRC/CAFÉ.PY", "src/Café.py"),
    ("Tests/X.PY", "tests/x.py"),
    ("agents.md", "AGENTS.md"),
    ("SRC/new/Missing.py", "src/new/Missing.py"),
    ("TESTS/New_File.py", "tests/New_File.py"),
    ("src/../SRC/vec.py", "src/vec.py"),
    ("lnk/vec.py", "src/vec.py"),
    ("lnk/VEC.py", "src/vec.py"),
    ("alias.py", "src/vec.py"),
    ("", ""),
]
OUTSIDE = [
    "../repo-other/x.py",
    "../repo-other/new.py",
    "src/../../repo-other/x.py",
    "../elsewhere/deep/new.py",
]


@HOOKS
@pytest.mark.parametrize("spelled, expected", INSIDE)
def test_canonical_respells_the_target_with_the_names_the_filesystem_stores(hook, tree, spelled, expected):
    assert hook.canonical(tree / spelled, tree, FS.samefile, FS.scandir) == tree / expected


@HOOKS
def test_canonical_recognises_a_root_prefix_spelled_in_other_case(hook, tree):
    target = Path(str(tree).upper()) / "SRC" / "VEC.PY"
    assert hook.canonical(target, tree, FS.samefile, FS.scandir) == tree / "src" / "vec.py"


@HOOKS
@pytest.mark.parametrize("spelled", OUTSIDE)
def test_canonical_is_none_outside_the_root(hook, tree, spelled):
    assert hook.canonical(tree / spelled, tree, FS.samefile, FS.scandir) is None


@HOOKS
def test_canonical_is_none_for_a_path_that_exists_nowhere(hook, tree):
    assert hook.canonical(Path("/nonexistent-zz/x.py"), tree, FS.samefile, FS.scandir) is None


@HOOKS
def test_canonical_raises_when_a_directory_inside_the_root_cannot_be_listed(hook, tree):
    with pytest.raises(PermissionError, match=REFUSAL):
        hook.canonical(tree / "SRC" / "vec.py", tree, FS.samefile, refuse)


@HOOKS
def test_canonical_is_none_for_a_path_the_filesystem_refuses_outside_the_root(hook, tree):
    def samefile(first, second):
        if not Path(first).is_relative_to(tree):
            raise PermissionError(REFUSAL)
        return FS.samefile(first, second)

    assert hook.canonical(tree.parent / "repo-other" / "x.py", tree, samefile, FS.scandir) is None


@HOOKS
def test_canonical_raises_when_the_root_itself_cannot_be_examined(hook, tree):
    with pytest.raises(PermissionError, match=REFUSAL):
        hook.canonical(tree.parent / "repo-other" / "x.py", tree, refuse, FS.scandir)


# T1, on the real primitives: what the hooks run with


@HOOKS
@pytest.mark.parametrize("spelled, expected", [
    ("src/vec.py", "src/vec.py"),
    ("src/Deep/File.py", "src/Deep/File.py"),
    ("lnk/vec.py", "src/vec.py"),
    ("alias.py", "src/vec.py"),
    ("src/new/Missing.py", "src/new/Missing.py"),
    ("src/../tests/x.py", "tests/x.py"),
    ("", ""),
])
def test_canonical_with_the_os_primitives_keeps_an_exact_spelling(hook, tree, spelled, expected):
    assert hook.canonical(tree / spelled, tree) == tree / expected


@HOOKS
def test_canonical_with_the_os_primitives_is_none_outside_the_root(hook, tree):
    assert hook.canonical(tree.parent / "repo-other" / "x.py", tree) is None


@HOOKS
def test_an_exact_spelling_is_never_replaced_by_another_name_of_the_same_file(hook, tmp_path):
    root = tmp_path.resolve()
    (root / "a.py").write_text("", encoding="utf-8")
    os.link(root / "a.py", root / "b.py")
    for name in ("a.py", "b.py"):
        assert hook.canonical(root / name, root) == root / name


def case_insensitive(directory):
    (directory / "Probe.tmp").write_text("", encoding="utf-8")
    return (directory / "PROBE.TMP").exists()


# T7: the real filesystem, where it ignores case


@HOOKS
def test_on_a_case_insensitive_filesystem_a_real_variant_is_respelled(hook, tree):
    if not case_insensitive(tree):
        pytest.skip("the filesystem under tmp_path is case-sensitive: a variant names no file here")
    target = Path(str(tree).upper()) / "SRC" / "DEEP" / "FILE.PY"
    assert hook.canonical(target, tree) == tree / "src" / "Deep" / "File.py"


# T6: the two copies, and the boundary hook's startup surface


def _copies(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
    return {node.name: ast.dump(node) for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in ("canonical", "_same")}


def test_the_two_copies_are_the_same_code():
    boundary = _copies(BOUNDARY_HOOK_FILE)
    assert set(boundary) == {"canonical", "_same"}
    assert boundary == _copies(CONTRACT_HOOK_FILE)


def _boundary_tree():
    return ast.parse(BOUNDARY_HOOK_FILE.read_text(encoding="utf-8"), feature_version=(3, 9))


def test_the_boundary_hook_postpones_annotations():
    assert any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in _boundary_tree().body)


def test_the_boundary_hook_imports_only_the_standard_library_and_the_gate_at_any_depth():
    roots = set()
    for node in ast.walk(_boundary_tree()):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add("." * node.level + (node.module or "").split(".")[0])
    assert roots <= set(sys.stdlib_module_names) | {"traianus"}, roots


# T2: the boundary hook, end to end

GOVERNED = [
    ("tests/x.py", f"{REPO_ROOT}/TESTS/x.py"),
    ("AGENTS.md", f"{REPO_ROOT}/agents.md"),
    ("traianus/app.py", f"{REPO_ROOT}/TRAIANUS/app.py"),
    ("docs/specifications/x.md", f"{REPO_ROOT}/Docs/SPECIFICATIONS/x.md"),
    ("traianus/security/hook_gate.py", f"{REPO_ROOT}/Traianus/Security/Hook_Gate.py"),
    ("tests/x.py", f"{SHOUT}/tests/x.py"),
    ("tests/x.py", f"{SWAP}/Tests/x.py"),
]
UNGOVERNED = [
    f"{REPO_ROOT}/tools/x.py",
    f"{REPO_ROOT}/Tools/x.py",
    f"{REPO_ROOT}/DOCS/roadmap/x.md",
    f"{REPO_ROOT}/Docs/Roadmap/NEXT_RESEARCH.md",
    f"{REPO_ROOT}/.CLAUDE/settings.json",
    f"{SHOUT}/tools/x.py",
]


@pytest.fixture
def audit(isolate_db):
    """The audit trail exists and holds a receipt for another file; `grant` adds one for a target."""
    def grant(target):
        decision = validate_proposal(json.dumps({
            "Intent_Class": "DOC", "Target_File": target, "Topological_Grounding": "q",
            "Implementation_Block": "b", "Safety_Abort": "NONE",
        }), target)
        assert decision["final_decision"] == "EXECUTE_SAFE"

    grant("docs/decoy.md")
    return grant


def gate(monkeypatch, file_path, tool="Edit", **primitives):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return require_boundary_validation.main(**primitives)


@pytest.mark.parametrize("exact", [exact for exact, _variant in GOVERNED[:5]])
def test_the_exact_spelling_of_a_governed_path_is_denied_without_a_receipt(monkeypatch, capsys, audit, exact):
    assert gate(monkeypatch, str(REPO_ROOT / exact)) == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err


@pytest.mark.parametrize("variant", [variant for _exact, variant in GOVERNED])
def test_a_governed_path_in_other_case_is_denied_without_a_receipt(monkeypatch, capsys, audit, variant):
    assert gate(monkeypatch, variant, **BLIND) == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err


def test_the_denial_names_the_path_as_the_filesystem_stores_it(monkeypatch, capsys, audit):
    assert gate(monkeypatch, f"{REPO_ROOT}/TESTS/x.py", **BLIND) == 2
    assert str(REPO_ROOT / "tests" / "x.py") in capsys.readouterr().err


@pytest.mark.parametrize("path", UNGOVERNED)
def test_an_ungoverned_path_is_allowed_in_any_case(monkeypatch, audit, path):
    assert gate(monkeypatch, path, **BLIND) == 0


@pytest.mark.parametrize("exact, variant", GOVERNED)
def test_a_receipt_for_the_exact_spelling_covers_its_case_variants(monkeypatch, audit, exact, variant):
    audit(exact)
    assert gate(monkeypatch, variant, **BLIND) == 0


def test_a_receipt_for_another_file_covers_no_variant(monkeypatch, capsys, audit):
    audit("tests/y.py")
    assert gate(monkeypatch, f"{REPO_ROOT}/TESTS/x.py", **BLIND) == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err


def test_the_hook_runs_with_the_os_primitives_unless_told_otherwise(monkeypatch, capsys, audit):
    assert gate(monkeypatch, str(REPO_ROOT / "tests" / "x.py")) == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err
    assert gate(monkeypatch, str(REPO_ROOT / "tools" / "x.py")) == 0


# T5: fail closed


def test_a_directory_that_cannot_be_listed_inside_the_root_denies(monkeypatch, capsys, audit):
    assert gate(monkeypatch, f"{REPO_ROOT}/TESTS/x.py", samefile=FS.samefile, scandir=refuse) == 2
    err = capsys.readouterr().err
    assert "fail-closed" in err
    assert f"{REPO_ROOT}/TESTS/x.py" in err
    assert REFUSAL in err


def test_a_path_the_filesystem_refuses_outside_the_root_is_allowed(monkeypatch, tmp_path, audit):
    def samefile(first, second):
        if not Path(first).is_relative_to(REPO_ROOT):
            raise PermissionError(REFUSAL)
        return FS.samefile(first, second)

    outside = tmp_path.resolve() / "x.py"
    assert gate(monkeypatch, str(outside), samefile=samefile, scandir=FS.scandir) == 0


def test_an_unreadable_root_denies_instead_of_reading_every_path_as_outside(monkeypatch, capsys, tmp_path, audit):
    outside = tmp_path.resolve() / "x.py"
    assert gate(monkeypatch, str(outside), samefile=refuse, scandir=FS.scandir) == 2
    assert REFUSAL in capsys.readouterr().err


def test_a_file_path_that_is_not_text_still_denies(monkeypatch, audit):
    assert gate(monkeypatch, 5, **BLIND) == 2


def test_a_path_that_cannot_be_resolved_denies_with_the_path_and_the_cause(monkeypatch, capsys, audit):
    assert gate(monkeypatch, f"{REPO_ROOT}/tests/x\x00.py") == 2
    err = capsys.readouterr().err
    assert "cannot tell whether" in err
    assert "null" in err


def test_a_symlink_loop_denies(monkeypatch, capsys, tmp_path, audit):
    loop = tmp_path.resolve() / "loop"
    loop.symlink_to(loop)
    assert gate(monkeypatch, str(loop / "x.py")) == 2
    assert "fail-closed" in capsys.readouterr().err


def test_a_home_relative_path_is_expanded_before_it_is_decided(monkeypatch, capsys, audit):
    monkeypatch.setenv("HOME", str(REPO_ROOT / "tests"))
    assert gate(monkeypatch, "~/x.py") == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep"])
def test_a_tool_other_than_edit_and_write_never_reaches_the_filesystem(monkeypatch, tool):
    assert gate(monkeypatch, f"{REPO_ROOT}/TESTS/x.py", tool, samefile=refuse, scandir=refuse) == 0


# T7: the boundary hook on the real repository, where the filesystem ignores case


@pytest.mark.parametrize("spelled", ["TESTS/conftest.py", "agents.md", "Traianus/app.py"])
def test_on_a_case_insensitive_filesystem_the_real_variants_are_denied(monkeypatch, capsys, audit, spelled):
    if not (REPO_ROOT / "TESTS").exists():
        pytest.skip("the repository sits on a case-sensitive filesystem: a variant names no file here")
    assert gate(monkeypatch, str(REPO_ROOT / spelled)) == 2
    assert "no recent EXECUTE_SAFE" in capsys.readouterr().err
