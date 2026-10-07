"""
The git pre-commit check: a staged governed path must equal the file on disk (docs/design/SANDBOX.md, section 9).

Git runs only through tools.audit.run_process, in repositories under tmp_path. The in-process tests call main()
inside such a repository with the project configuration repointed (config_file); the end-to-end tests commit in a
repository that carries a copy of the kit and a real .git/hooks/pre-commit.
"""
import ast
import json
import os
import sys
from pathlib import Path

import pytest

from tools.audit import run_process
from tools.git import commit_integrity

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "git" / "commit_integrity.py"
HOOK = REPO_ROOT / "tools" / "git" / "pre-commit"
KIT = (
    "tools/__init__.py",
    "tools/project_config.py",
    "tools/audit/__init__.py",
    "tools/audit/run_process.py",
    "tools/git/commit_integrity.py",
)
CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["gov/**"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 900,
}
PREFIX = "[commit_integrity]"
RULE = 'governed_paths entry "gov/**"'
ALLOWED_KIT_IMPORTS = {"tools.project_config", "tools.audit.run_process"}


@pytest.fixture(autouse=True)
def clean_git_environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo, *args, stdin=""):
    return run_process.run(["git", *args], cwd=repo, stdin=stdin)


def must(repo, *args, stdin=""):
    done = git(repo, *args, stdin=stdin)
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
    return done.stdout.strip()


def new_repo(root):
    root.mkdir()
    must(root, "init", "-q")
    must(root, "config", "user.name", "Test")
    must(root, "config", "user.email", "test@example.com")
    must(root, "config", "commit.gpgsign", "false")
    return root


def put(repo, rel, content):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def stage_blob(repo, rel, content, mode="100644"):
    """Stages `content` for `rel` without touching the disk, as `git checkout <commit> -- <path>` does when it
    fails to write the file, or `git hash-object -w` with `git update-index` does on purpose."""
    blob = must(repo, "hash-object", "-w", "--stdin", stdin=content)
    must(repo, "update-index", "--add", "--cacheinfo", f"{mode},{blob},{rel}")


def head(repo):
    return must(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, config_file, monkeypatch):
    """A repository with no commit, the project configuration governing gov/**, and the current directory in it."""
    config_file(CONFIG)
    root = new_repo(tmp_path / "repo")
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def committed(repo):
    """Two commits: gov/a.txt was `old` and is `one`; gov/b.txt, other/o.txt and other/p.txt are as committed."""
    put(repo, "gov/a.txt", "old\n")
    put(repo, "gov/b.txt", "b\n")
    put(repo, "other/o.txt", "o\n")
    put(repo, "other/p.txt", "p\n")
    must(repo, "add", "-A")
    must(repo, "commit", "-q", "-m", "first")
    put(repo, "gov/a.txt", "one\n")
    must(repo, "add", "-A")
    must(repo, "commit", "-q", "-m", "second")
    return repo


def run_check(capsys):
    code = commit_integrity.main()
    captured = capsys.readouterr()
    assert captured.out == ""
    return code, captured.err.splitlines()


def assert_accepted(capsys):
    assert run_check(capsys) == (0, [])


def assert_refused(capsys, rel, what):
    """One mismatching path: its line names the path, what differs, the rule and its source; then the way out."""
    code, lines = run_check(capsys)
    assert code == 1
    assert len(lines) == 2 and all(line.startswith(PREFIX) for line in lines), lines
    path_line, way_out = lines
    assert rel in path_line and what in path_line
    assert RULE in path_line and ".actuarii.json" in path_line
    assert "gate" in way_out and "stage the whole file" in way_out and "git restore --staged <path>" in way_out
    assert "AGENTS" not in "".join(lines)


# T1: the staged blob differs from the disk


def test_an_older_blob_staged_over_an_unchanged_file_is_refused_the_s8_case(committed, capsys):
    stage_blob(committed, "gov/a.txt", must(committed, "show", "HEAD~1:gov/a.txt") + "\n")
    assert_refused(capsys, "gov/a.txt", "the staged content differs from the file on disk")


def test_a_forged_blob_written_with_hash_object_and_staged_with_update_index_is_refused(committed, capsys):
    stage_blob(committed, "gov/a.txt", "never written by the gate\n")
    assert_refused(capsys, "gov/a.txt", "the staged content differs from the file on disk")


def test_a_governed_file_changed_on_disk_after_it_was_staged_is_refused(committed, capsys):
    put(committed, "gov/a.txt", "two\n")
    must(committed, "add", "gov/a.txt")
    put(committed, "gov/a.txt", "three\n")
    assert_refused(capsys, "gov/a.txt", "the staged content differs from the file on disk")


def test_a_new_governed_file_staged_with_other_content_than_the_disk_is_refused(committed, capsys):
    stage_blob(committed, "gov/new.txt", "staged\n")
    put(committed, "gov/new.txt", "on disk\n")
    assert_refused(capsys, "gov/new.txt", "the staged content differs from the file on disk")


def test_every_mismatching_path_gets_a_line_and_the_way_out_comes_once(committed, capsys):
    stage_blob(committed, "gov/a.txt", "forged a\n")
    stage_blob(committed, "gov/b.txt", "forged b\n")
    code, lines = run_check(capsys)
    assert code == 1 and len(lines) == 3 and all(line.startswith(PREFIX) for line in lines)
    assert "gov/a.txt" in lines[0] and "gov/b.txt" in lines[1] and "git restore --staged" in lines[2]


# T2: the other mismatches


def test_a_staged_deletion_of_a_governed_file_still_on_disk_is_refused(committed, capsys):
    must(committed, "rm", "--cached", "-q", "gov/a.txt")
    assert_refused(capsys, "gov/a.txt", "a staged deletion of a file that is still on disk")


def test_a_staged_governed_file_that_is_not_on_disk_is_refused(committed, capsys):
    put(committed, "gov/new.txt", "new\n")
    must(committed, "add", "gov/new.txt")
    (committed / "gov" / "new.txt").unlink()
    assert_refused(capsys, "gov/new.txt", "a staged file that is not on disk")


def test_a_governed_file_made_executable_on_disk_after_it_was_staged_is_refused(committed, capsys):
    put(committed, "gov/run.sh", "echo\n")
    must(committed, "add", "gov/run.sh")
    (committed / "gov" / "run.sh").chmod(0o755)
    assert_refused(capsys, "gov/run.sh", "the staged mode differs from the file on disk")


def test_a_governed_file_staged_as_executable_but_not_executable_on_disk_is_refused(committed, capsys):
    put(committed, "gov/run.sh", "echo\n")
    must(committed, "add", "--chmod=+x", "gov/run.sh")
    assert_refused(capsys, "gov/run.sh", "the staged mode differs from the file on disk")


def test_a_symbolic_link_staged_at_a_governed_path_is_refused(committed, capsys):
    (committed / "gov" / "link").symlink_to("a.txt")
    must(committed, "add", "gov/link")
    assert_refused(capsys, "gov/link", "not a regular file")


def test_a_regular_file_staged_where_the_disk_has_a_symbolic_link_is_refused(committed, capsys):
    put(committed, "gov/f.txt", "f\n")
    must(committed, "add", "gov/f.txt")
    (committed / "gov" / "f.txt").unlink()
    (committed / "gov" / "f.txt").symlink_to("a.txt")
    assert_refused(capsys, "gov/f.txt", "not a regular file")


def test_a_staged_deletion_where_the_disk_has_a_directory_is_refused(committed, capsys):
    must(committed, "rm", "--cached", "-q", "gov/a.txt")
    (committed / "gov" / "a.txt").unlink()
    (committed / "gov" / "a.txt").mkdir()
    assert_refused(capsys, "gov/a.txt", "not a regular file")


def test_a_rename_out_of_a_governed_path_leaves_a_deletion_that_is_refused_while_the_file_is_on_disk(
    committed, capsys
):
    must(committed, "mv", "gov/b.txt", "other/b.txt")
    put(committed, "gov/b.txt", "again\n")
    assert_refused(capsys, "gov/b.txt", "a staged deletion of a file that is still on disk")


# T3: no false refusals


def test_a_governed_change_staged_whole_passes(committed, capsys):
    put(committed, "gov/a.txt", "two\n")
    must(committed, "add", "gov/a.txt")
    assert_accepted(capsys)


def test_a_governed_addition_and_a_governed_deletion_staged_with_the_disk_in_step_pass(committed, capsys):
    put(committed, "gov/new.txt", "new\n")
    (committed / "gov" / "b.txt").unlink()
    must(committed, "add", "-A")
    assert_accepted(capsys)


def test_an_executable_governed_file_staged_as_executable_passes(committed, capsys):
    put(committed, "gov/run.sh", "echo\n")
    (committed / "gov" / "run.sh").chmod(0o755)
    must(committed, "add", "gov/run.sh")
    assert must(committed, "ls-files", "--stage", "gov/run.sh").startswith("100755")
    assert_accepted(capsys)


def test_a_governed_file_the_repository_filters_on_staging_is_compared_as_git_would_store_it(committed, capsys):
    put(committed, ".gitattributes", "gov/*.txt text eol=lf\n")
    put(committed, "gov/crlf.txt", b"x\r\ny\r\n")
    must(committed, "add", ".gitattributes", "gov/crlf.txt")
    assert must(committed, "show", ":gov/crlf.txt") == "x\ny"
    assert_accepted(capsys)


def test_ungoverned_paths_are_never_checked_whatever_their_index_state(committed, capsys):
    stage_blob(committed, "other/o.txt", "forged\n")
    must(committed, "rm", "--cached", "-q", "other/p.txt")
    put(committed, "other/new.txt", "new\n")
    must(committed, "add", "other/new.txt")
    (committed / "other" / "new.txt").unlink()
    assert_accepted(capsys)


def test_a_commit_that_stages_nothing_passes(committed, capsys):
    assert_accepted(capsys)


def test_a_rename_from_a_governed_path_to_an_ungoverned_one_passes(committed, capsys):
    must(committed, "mv", "gov/b.txt", "other/b.txt")
    assert_accepted(capsys)


def test_a_rename_from_an_ungoverned_path_to_a_governed_one_passes(committed, capsys):
    must(committed, "mv", "other/p.txt", "gov/p.txt")
    assert_accepted(capsys)


def test_the_first_commit_is_checked_against_the_empty_tree(repo, capsys):
    put(repo, "gov/a.txt", "one\n")
    must(repo, "add", "gov/a.txt")
    assert_accepted(capsys)


def test_the_first_commit_with_a_governed_mismatch_is_refused(repo, capsys):
    stage_blob(repo, "gov/a.txt", "forged\n")
    put(repo, "gov/a.txt", "one\n")
    assert_refused(capsys, "gov/a.txt", "the staged content differs from the file on disk")


# T7: a staged path is spelled as the disk spells it


def _tells_case_apart(directory):
    probe = directory / "Case-Probe"
    probe.write_text("x", encoding="utf-8")
    try:
        return not (directory / "case-probe").exists()
    finally:
        probe.unlink()


@pytest.fixture
def case_insensitive(tmp_path):
    if _tells_case_apart(tmp_path):
        pytest.skip("the filesystem of tmp_path tells names apart by case")


def assert_misspelled(capsys, rel, part, on_disk):
    code, lines = run_check(capsys)
    assert code == 1
    assert len(lines) == 2 and all(line.startswith(PREFIX) for line in lines), lines
    path_line, way_out = lines
    assert rel in path_line and f"'{part}' is listed as '{on_disk}'" in path_line
    assert "the staged spelling differs from the name on disk" in path_line
    assert "stage the whole file" in way_out and "git restore --staged <path>" in way_out


def test_a_case_variant_of_a_committed_governed_directory_is_refused(committed, capsys, case_insensitive):
    stage_blob(committed, "GOV/a.txt", "forged\n")
    assert_misspelled(capsys, "GOV/a.txt", "GOV", "gov")


def test_a_case_variant_of_a_committed_governed_file_name_is_refused(committed, capsys, case_insensitive):
    stage_blob(committed, "gov/A.txt", "forged\n")
    assert_misspelled(capsys, "gov/A.txt", "A.txt", "a.txt")


def test_a_new_file_under_a_case_variant_of_an_existing_directory_is_refused(committed, capsys, case_insensitive):
    stage_blob(committed, "GOV/new.txt", "forged\n")
    assert_misspelled(capsys, "GOV/new.txt", "GOV", "gov")


def test_an_ungoverned_case_variant_is_refused_too(committed, capsys, case_insensitive):
    stage_blob(committed, "Other/o.txt", "forged\n")
    assert_misspelled(capsys, "Other/o.txt", "Other", "other")


def test_a_new_directory_with_a_new_file_passes(committed, capsys):
    put(committed, "fresh/deeper/f.txt", "f\n")
    must(committed, "add", "fresh/deeper/f.txt")
    assert_accepted(capsys)


def test_a_new_file_in_an_existing_directory_spelled_as_on_disk_passes(committed, capsys):
    put(committed, "gov/new.txt", "n\n")
    put(committed, "other/new.txt", "n\n")
    must(committed, "add", "-A")
    assert_accepted(capsys)


def test_a_deletion_of_existing_paths_spelled_as_on_disk_passes(committed, capsys):
    must(committed, "rm", "-q", "gov/b.txt", "other/p.txt")
    assert_accepted(capsys)


def test_a_directory_that_cannot_be_listed_refuses_the_commit(committed, monkeypatch, capsys):
    put(committed, "other/o.txt", "changed\n")
    must(committed, "add", "other/o.txt")

    def denied(path="."):
        raise PermissionError(13, "denied", str(path))

    monkeypatch.setattr(os, "listdir", denied)
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)
    assert "denied" in "\n".join(lines)


def test_a_real_commit_of_a_case_variant_of_a_governed_file_is_refused_through_the_hook(hooked, case_insensitive):
    before = head(hooked)
    stage_blob(hooked, "GOV/a.txt", "forged\n")
    refused = git(hooked, "commit", "-q", "-m", "variant")
    assert refused.returncode != 0
    assert PREFIX in refused.stderr and "GOV/a.txt" in refused.stderr and "'GOV' is listed as 'gov'" in refused.stderr
    assert head(hooked) == before


# T5 and the temporary index of `git commit -a` and `git commit <path>`: a real commit, through the hook


@pytest.fixture
def hooked(tmp_path, monkeypatch):
    """A repository with a copy of the kit, gov/** governed, two commits (gov/a.txt was `old`, is `one`) and
    the hook installed as git would run it; `python3` on the PATH is the interpreter running the tests."""
    root = new_repo(tmp_path / "hooked")
    for rel in KIT:
        put(root, rel, (REPO_ROOT / rel).read_bytes())
    put(root, ".actuarii.json", json.dumps(CONFIG))
    put(root, "gov/a.txt", "old\n")
    put(root, "gov/b.txt", "b\n")
    put(root, "other/o.txt", "o\n")
    must(root, "add", "-A")
    must(root, "commit", "-q", "-m", "first")
    installed = root / ".git" / "hooks" / "pre-commit"
    installed.write_bytes(HOOK.read_bytes())
    installed.chmod(0o755)
    interpreters = tmp_path / "bin"
    interpreters.mkdir()
    (interpreters / "python3").symlink_to(sys.executable)
    monkeypatch.setenv("PATH", f"{interpreters}{os.pathsep}{os.environ['PATH']}")
    put(root, "gov/a.txt", "one\n")
    must(root, "add", "gov/a.txt")
    must(root, "commit", "-q", "-m", "second")
    return root


def test_a_real_commit_with_an_older_blob_staged_is_refused_and_accepted_once_the_index_matches_the_disk(hooked):
    before = head(hooked)
    stage_blob(hooked, "gov/a.txt", "old\n")
    refused = git(hooked, "commit", "-q", "-m", "s8")
    assert refused.returncode != 0
    assert PREFIX in refused.stderr and "gov/a.txt" in refused.stderr and RULE in refused.stderr
    assert head(hooked) == before
    put(hooked, "gov/a.txt", "new\n")
    must(hooked, "add", "gov/a.txt")
    must(hooked, "commit", "-q", "-m", "through the gate")
    assert head(hooked) != before
    assert must(hooked, "show", "HEAD:gov/a.txt") == "new"


def test_the_hook_refuses_from_a_subdirectory_of_the_repository_too(hooked):
    before = head(hooked)
    stage_blob(hooked, "gov/a.txt", "old\n")
    refused = git(hooked / "gov", "commit", "-q", "-m", "s8")
    assert refused.returncode != 0 and "gov/a.txt" in refused.stderr
    assert head(hooked) == before


def test_a_real_commit_that_stages_no_governed_path_is_accepted(hooked):
    put(hooked, "other/o.txt", "changed\n")
    must(hooked, "add", "other/o.txt")
    must(hooked, "commit", "-q", "-m", "ungoverned")


def test_commit_a_is_checked_against_the_temporary_index_and_not_the_one_it_replaces(hooked):
    stage_blob(hooked, "gov/b.txt", "forged\n")
    put(hooked, "gov/a.txt", "two\n")
    must(hooked, "commit", "-q", "-a", "-m", "all")
    assert must(hooked, "show", "HEAD:gov/a.txt") == "two"
    assert must(hooked, "show", "HEAD:gov/b.txt") == "b"


def test_commit_of_a_path_is_checked_against_the_temporary_index_and_not_the_one_it_replaces(hooked):
    stage_blob(hooked, "gov/b.txt", "forged\n")
    put(hooked, "gov/a.txt", "two\n")
    must(hooked, "commit", "-q", "-m", "one path", "--", "gov/a.txt")
    assert must(hooked, "show", "HEAD:gov/a.txt") == "two"
    assert must(hooked, "show", "HEAD:gov/b.txt") == "b"


def test_commit_of_a_path_whose_staged_blob_differs_from_the_disk_is_refused_through_the_hook(hooked):
    before = head(hooked)
    put(hooked, "gov/a.txt", "two\n")
    stage_blob(hooked, "gov/a.txt", "forged\n")
    put(hooked, "gov/a.txt", "three\n")
    refused = git(hooked, "commit", "-q", "-m", "x")
    assert refused.returncode != 0 and PREFIX in refused.stderr
    assert head(hooked) == before


def test_a_hook_whose_check_is_missing_refuses_the_commit(hooked):
    before = head(hooked)
    (hooked / "tools" / "git" / "commit_integrity.py").unlink()
    put(hooked, "other/o.txt", "changed\n")
    must(hooked, "add", "other/o.txt")
    assert git(hooked, "commit", "-q", "-m", "x").returncode != 0
    assert head(hooked) == before


@pytest.mark.parametrize("module", ["tools/project_config.py", "tools/audit/run_process.py"])
def test_a_check_whose_kit_modules_cannot_be_imported_refuses_the_commit_and_says_so(hooked, module):
    before = head(hooked)
    (hooked / module).unlink()
    put(hooked, "other/o.txt", "changed\n")
    must(hooked, "add", "other/o.txt")
    refused = git(hooked, "commit", "-q", "-m", "x")
    assert refused.returncode != 0 and PREFIX in refused.stderr
    assert head(hooked) == before


def test_the_hook_is_a_posix_sh_script_that_runs_the_check_at_the_top_of_the_repository():
    text = HOOK.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert "git rev-parse --show-toplevel" in text
    assert 'exec python3 "$top/tools/git/commit_integrity.py"' in text


# T4: fails closed


def test_an_invalid_project_configuration_refuses_the_commit(committed, config_file, capsys):
    config_file("{")
    put(committed, "other/o.txt", "changed\n")
    must(committed, "add", "other/o.txt")
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)
    assert ".actuarii.json" in "\n".join(lines)


def test_a_directory_that_is_not_a_repository_refuses(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)


def test_an_index_git_cannot_read_refuses(committed, capsys):
    (committed / ".git" / "index").write_bytes(b"not an index")
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)


def test_a_git_command_that_fails_refuses(committed, monkeypatch, capsys):
    monkeypatch.setattr(run_process, "run", lambda argv, **kwargs: run_process.Result(128, "", "fatal: boom"))
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)
    assert "boom" in "\n".join(lines)


def test_git_output_that_cannot_be_parsed_refuses(committed, monkeypatch, capsys):
    real = run_process.run

    def garbled(argv, **kwargs):
        done = real(argv, **kwargs)
        return run_process.Result(0, "not raw output", "") if "diff-index" in argv else done

    monkeypatch.setattr(run_process, "run", garbled)
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)


def test_an_unexpected_error_refuses_and_names_the_cause(committed, monkeypatch, capsys):
    def broken(argv, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(run_process, "run", broken)
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)
    assert "unexpected" in "\n".join(lines)


def test_a_git_that_cannot_start_refuses(committed, tmp_path, monkeypatch, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, lines = run_check(capsys)
    assert code == 1 and lines and all(line.startswith(PREFIX) for line in lines)


# T6: git must be able to start the check under a system Python 3.9


def _kit_imports(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            if node.module.split(".")[0] == "tools":
                names.update(f"{node.module}.{alias.name}" for alias in node.names)
            else:
                names.add(node.module)
    return names


def test_the_check_imports_only_the_standard_library_and_the_two_kit_modules():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 9))
    names = _kit_imports(tree)
    assert ALLOWED_KIT_IMPORTS <= names
    foreign = {name for name in names if name.split(".")[0] not in sys.stdlib_module_names} - ALLOWED_KIT_IMPORTS
    assert not foreign, sorted(foreign)


def test_the_check_postpones_annotations_and_parses_as_python_3_9():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), feature_version=(3, 9))
    assert any(
        isinstance(node, ast.ImportFrom) and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )
