"""The commit-msg hook records what recorded writes lead to for every governed path a commit changes (ADR-016).

Every case commits for real, in a git repository under tmp_path that holds a copy of the kit and has the copy's
tools/git/commit-msg installed as its .git/hooks/commit-msg. The receipts come from the copy's own validator and the
records from the copy's own gate, both started as processes, so that nothing here reads or writes the audit database or
the .git of the repository the tests run from. The python3 first on the PATH is the interpreter of the test run: the hook
runs the copy's script and never the shim of a session. The current user's git configuration is out of reach (HOME is
under tmp_path) and the identity of the commits is on the command line.
"""
import json
import os
import shutil
import sqlite3
import stat
import sys
from contextlib import closing
from pathlib import Path

import pytest

from tools.audit.run_process import run

CLONE = Path(__file__).resolve().parents[2]
HOOK = CLONE / "tools" / "git" / "commit-msg"
PRE_COMMIT = CLONE / "tools" / "git" / "pre-commit"
CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["gov/**", "star/*"],
    "python_script_dirs": [],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 900,
}
IDENTITY = ("-c", "user.name=Tester", "-c", "user.email=tester@example.org", "-c", "commit.gpgsign=false")
OUTSIDE = "Actuarii-Record: changed outside the channel: "
MATCHES = "Actuarii-Record: matches: "
RATIONALE = "Actuarii-Rationale: "
NOT_MADE = "Actuarii-Record: not made: "


class Repo:
    """A repository with a copy of the kit; `edit` and `write` do what a tool does: the gate first, the file after."""

    def __init__(self, root, env, interpreters):
        self.root = root
        self.env = env
        self.interpreters = interpreters

    def run(self, argv, cwd=None, stdin=""):
        return run(argv, cwd=cwd or self.root, env=self.env, stdin=stdin, timeout=120.0)

    def git(self, *args, cwd=None):
        done = self.run(["git", *args], cwd=cwd)
        assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
        return done

    def commit(self, *args, cwd=None, editor=None):
        """git commit as the person runs it, with `editor` as the program that edits the message; the result is not
        checked."""
        env = self.env if editor is None else {**self.env, "GIT_EDITOR": str(editor)}
        return run(["git", *IDENTITY, "commit", "-q", *args], cwd=cwd or self.root, env=env, timeout=120.0)

    def subject_editor(self):
        """An editor that writes `subject` above whatever git offers, as a person does."""
        editor = self.interpreters / "editor"
        editor.write_text("#!/bin/sh\n{ printf 'subject\\n\\n'; cat \"$1\"; } > \"$1.new\" && mv \"$1.new\" \"$1\"\n",
                          encoding="utf-8")
        editor.chmod(0o755)
        return editor

    def commit_all(self, message):
        self.git("add", "-A")
        return self.commit("-m", message)

    def message(self, revision="HEAD"):
        return self.git("cat-file", "commit", revision).stdout.split("\n\n", 1)[1]

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()

    def path(self, relative):
        return self.root / relative

    def put(self, relative, content):
        self.path(relative).parent.mkdir(parents=True, exist_ok=True)
        self.path(relative).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def read(self, relative):
        return self.path(relative).read_bytes().decode("utf-8")

    def receipt(self, relative, grounding, block, rationale):
        proposal = {"Intent_Class": "DOC", "Target_File": relative, "Topological_Grounding": grounding,
                    "Implementation_Block": block, "Safety_Abort": "NONE", "Rationale": rationale}
        script = self.root / "tools" / "boundary_validator" / "validator.py"
        done = self.run([sys.executable, str(script), json.dumps(proposal), relative])
        assert done.returncode == 0, done.stderr
        decision = json.loads(done.stdout)
        assert decision["final_decision"] == "EXECUTE_SAFE", decision

    def gate(self, tool, tool_input):
        payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(self.root)})
        done = self.run([sys.executable, str(self.root / "tools" / "hooks" / "require_boundary_validation.py")],
                        stdin=payload)
        assert done.returncode == 0, done.stderr

    def edit(self, relative, old, new, rationale, apply=True):
        """An Edit through the gate with its receipt; `apply=False` is a write the gate allowed and that never happened."""
        current = self.read(relative)
        self.receipt(relative, old, new, rationale)
        self.gate("Edit", {"file_path": str(self.path(relative)), "old_string": old, "new_string": new})
        if apply:
            self.put(relative, current.replace(old, new, 1))

    def write(self, relative, content, rationale, grounding=None):
        if grounding is None:
            grounding = self.read(relative).split("\n")[0] if self.path(relative).exists() else ""
        self.receipt(relative, grounding, content, rationale)
        self.gate("Write", {"file_path": str(self.path(relative)), "content": content})
        self.put(relative, content)

    def audit(self, sql):
        with closing(sqlite3.connect(self.root / ".data" / "boundary_validator_audit.db")) as conn, conn:
            conn.execute(sql)

    def install_hook(self):
        installed = self.root / ".git" / "hooks" / "commit-msg"
        installed.write_bytes((self.root / "tools" / "git" / "commit-msg").read_bytes())
        installed.chmod(0o755)


def make_repo(tmp_path):
    root, home, interpreters = tmp_path / "repo", tmp_path / "home", tmp_path / "bin"
    for directory in (home, interpreters):
        directory.mkdir()
    (interpreters / "python3").symlink_to(sys.executable)
    shutil.copytree(CLONE / "tools", root / "tools", symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    env = {name: os.environ[name] for name in ("TMPDIR",) if name in os.environ}
    env.update({"PATH": f"{interpreters}{os.pathsep}{os.environ['PATH']}", "HOME": str(home),
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_EDITOR": "true", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"})
    repo = Repo(root.resolve(), env, interpreters)
    repo.git("init", "-q")
    repo.put(".actuarii.json", json.dumps(CONFIG))
    repo.put(".gitignore", ".data/\n__pycache__/\n")
    return repo


@pytest.fixture
def repo(tmp_path):
    """A repository whose first commit holds the kit, the configuration (it governs gov/**) and three files; the hook
    is installed after that commit."""
    repo = make_repo(tmp_path)
    repo.put("gov/a.txt", "alpha\n")
    repo.put("gov/b.txt", "bravo\n")
    repo.put("other/o.txt", "omega\n")
    repo.git("add", "-A")
    assert repo.commit("-m", "base").returncode == 0
    repo.install_hook()
    return repo


@pytest.fixture
def unborn(tmp_path):
    """The same repository before its first commit, with the hook installed and no governed file but the configuration."""
    repo = make_repo(tmp_path)
    repo.install_hook()
    return repo


def lines(*entries):
    return "\n".join(entries) + "\n"


def message_of(subject, *entries):
    return subject + "\n\n" + lines(*entries)


def committed(repo, subject="subject"):
    done = repo.commit_all(subject)
    assert done.returncode == 0, done.stderr
    return repo.message()


# T5: a governed file written through the gate, and one changed without it


def test_a_governed_file_written_through_the_gate_is_committed_with_its_record_and_its_rationale(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "Shout the first letter.")
    assert committed(repo, "change a") == message_of(
        "change a", MATCHES + "gov/a.txt", RATIONALE + "Shout the first letter.")


def test_a_governed_file_changed_without_the_gate_is_committed_as_changed_outside_the_channel(repo):
    repo.put("gov/a.txt", "by hand\n")
    assert committed(repo, "change a") == message_of("change a", OUTSIDE + "gov/a.txt")


def test_a_commit_that_goes_well_says_nothing_on_stderr(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    done = repo.commit_all("change a")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_the_record_is_made_from_a_subdirectory_of_the_repository_too(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    repo.git("add", "-A")
    assert repo.commit("-m", "from gov", cwd=repo.path("gov")).returncode == 0
    assert repo.message() == message_of("from gov", MATCHES + "gov/a.txt", RATIONALE + "A reason.")


@pytest.mark.parametrize("arguments", [("-a", "-m", "all"), ("-m", "one path", "--", "gov/a.txt")],
                         ids=["commit-a", "commit-path"])
def test_the_record_is_made_from_the_temporary_index_of_commit_a_and_commit_path(repo, arguments):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    assert repo.commit(*arguments).returncode == 0
    assert repo.message() == message_of(arguments[arguments.index("-m") + 1], MATCHES + "gov/a.txt",
                                        RATIONALE + "A reason.")


# T6: the chain and the lines


def test_two_gated_edits_of_a_file_are_one_matches_line_with_their_distinct_rationales_in_order(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "First reason.")
    repo.edit("gov/a.txt", "beta", "gamma", "Second reason.")
    assert committed(repo) == message_of(
        "subject", MATCHES + "gov/a.txt", RATIONALE + "First reason.", RATIONALE + "Second reason.")


def test_a_rationale_that_repeats_is_written_once_where_it_first_appears(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "One reason.")
    repo.edit("gov/a.txt", "beta", "gamma", "Another reason.")
    repo.edit("gov/a.txt", "gamma", "delta", "One reason.")
    assert committed(repo) == message_of(
        "subject", MATCHES + "gov/a.txt", RATIONALE + "One reason.", RATIONALE + "Another reason.")


def test_a_write_the_gate_allowed_and_that_never_happened_does_not_spoil_the_match_nor_add_its_rationale(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "Never made.", apply=False)
    repo.edit("gov/a.txt", "alpha", "gamma", "Made.")
    assert committed(repo) == message_of("subject", MATCHES + "gov/a.txt", RATIONALE + "Made.")


def test_a_write_the_gate_allowed_and_that_never_happened_counts_when_the_same_content_arrives_by_hand(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "Never made.", apply=False)
    repo.put("gov/a.txt", "beta\n")
    assert committed(repo) == message_of("subject", MATCHES + "gov/a.txt", RATIONALE + "Never made.")


def test_a_write_the_gate_allowed_and_that_never_happened_does_not_cover_another_content_by_hand(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "Never made.", apply=False)
    repo.put("gov/a.txt", "by hand\n")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/a.txt")


def test_an_edit_by_hand_before_a_gated_edit_is_changed_outside_the_channel(repo):
    repo.put("gov/a.txt", "by hand\n")
    repo.edit("gov/a.txt", "by hand", "gated", "After the hand.")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/a.txt")


def test_an_edit_by_hand_after_a_gated_edit_is_changed_outside_the_channel(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "Before the hand.")
    repo.put("gov/a.txt", "beta and more\n")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/a.txt")


def test_a_deletion_is_changed_outside_the_channel(repo):
    repo.path("gov/b.txt").unlink()
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/b.txt")


def test_a_deletion_is_changed_outside_the_channel_even_after_a_gated_edit(repo):
    repo.edit("gov/b.txt", "bravo", "BRAVO", "A reason.")
    repo.path("gov/b.txt").unlink()
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/b.txt")


def test_a_new_file_written_through_the_gate_matches_from_absent(repo):
    repo.write("gov/new.txt", "fresh\n", "Add the file.")
    assert committed(repo) == message_of("subject", MATCHES + "gov/new.txt", RATIONALE + "Add the file.")


def test_a_new_file_created_by_hand_is_changed_outside_the_channel(repo):
    repo.put("gov/new.txt", "fresh\n")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/new.txt")


def test_a_write_over_a_file_matches_from_the_content_at_head(repo):
    repo.write("gov/a.txt", "rewritten\n", "Rewrite the file.")
    assert committed(repo) == message_of("subject", MATCHES + "gov/a.txt", RATIONALE + "Rewrite the file.")


def test_each_commit_is_compared_with_the_content_at_head_and_not_with_the_whole_history(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "First commit.")
    assert committed(repo, "first") == message_of("first", MATCHES + "gov/a.txt", RATIONALE + "First commit.")
    repo.edit("gov/a.txt", "beta", "gamma", "Second commit.")
    assert committed(repo, "second") == message_of("second", MATCHES + "gov/a.txt", RATIONALE + "Second commit.")


def test_a_governed_file_edited_and_put_back_as_it_was_gets_no_line(repo):
    repo.edit("gov/a.txt", "alpha", "beta", "There.")
    repo.edit("gov/a.txt", "beta", "alpha", "And back.")
    repo.put("other/o.txt", "changed\n")
    assert committed(repo) == "subject\n"


def test_every_governed_path_gets_its_lines_in_the_order_of_git_and_the_others_get_none(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "Reason for a.")
    repo.put("gov/b.txt", "by hand\n")
    repo.write("gov/c.txt", "charlie\n", "Reason for c.")
    repo.put("other/o.txt", "changed\n")
    assert committed(repo) == message_of(
        "subject",
        MATCHES + "gov/a.txt", RATIONALE + "Reason for a.",
        OUTSIDE + "gov/b.txt",
        MATCHES + "gov/c.txt", RATIONALE + "Reason for c.")


def test_a_rename_is_a_deletion_and_an_addition(repo):
    repo.git("mv", "gov/b.txt", "gov/c.txt")
    assert repo.commit("-m", "rename").returncode == 0
    assert repo.message() == message_of("rename", OUTSIDE + "gov/b.txt", OUTSIDE + "gov/c.txt")


def test_the_configuration_file_is_governed_whatever_it_says(repo):
    repo.put(".actuarii.json", json.dumps({**CONFIG, "receipt_window_seconds": 60}))
    assert committed(repo) == message_of("subject", OUTSIDE + ".actuarii.json")


def test_a_change_of_mode_alone_gets_no_line(repo):
    repo.path("gov/a.txt").chmod(0o755)
    repo.git("add", "-A")
    assert "mode change 100644 => 100755 gov/a.txt" in repo.git("diff", "--cached", "--summary").stdout
    assert repo.commit("-m", "mode").returncode == 0
    assert repo.message() == "mode\n"


def test_a_path_that_no_rule_governs_gets_no_line(repo):
    repo.put("other/o.txt", "changed\n")
    repo.put("other/new.txt", "new\n")
    assert committed(repo) == "subject\n"


def test_a_gitlink_gets_no_line_and_the_other_paths_still_do(repo):
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{repo.head()},gov/sub")
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    repo.git("add", "gov/a.txt")
    assert repo.commit("-m", "with a gitlink").returncode == 0
    assert repo.git("ls-tree", "HEAD", "gov/sub").stdout.startswith("160000 commit")
    assert repo.message() == message_of("with a gitlink", MATCHES + "gov/a.txt", RATIONALE + "A reason.")


def test_the_first_commit_is_compared_with_the_empty_tree(unborn):
    unborn.write("gov/a.txt", "first\n", "Start the file.")
    assert committed(unborn, "first") == message_of(
        "first", OUTSIDE + ".actuarii.json", MATCHES + "gov/a.txt", RATIONALE + "Start the file.")


def test_the_first_commit_of_a_governed_file_written_by_hand_is_changed_outside_the_channel(unborn):
    unborn.put("gov/a.txt", "first\n")
    assert committed(unborn, "first") == message_of(
        "first", OUTSIDE + ".actuarii.json", OUTSIDE + "gov/a.txt")


def test_a_committed_governed_file_that_is_not_utf8_is_changed_outside_the_channel_and_the_record_is_made(repo):
    repo.put("gov/binary.dat", b"\xff\xfe\x00 binary")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/binary.dat")


def test_no_recorded_write_starts_from_a_base_that_is_not_utf8(repo):
    repo.put("gov/binary.dat", b"text \xff\xfe")
    assert repo.commit_all("binary").returncode == 0
    repo.write("gov/binary.dat", "now text\n", "Replace the bytes.", grounding="text")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/binary.dat")


def test_two_different_blobs_that_are_not_utf8_do_not_match_each_other(repo):
    repo.put("gov/binary.dat", b"text \xff\xfe")
    assert repo.commit_all("binary").returncode == 0
    repo.put("gov/binary.dat", b"other \xff\xfd")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/binary.dat")


def test_a_rationale_with_line_breaks_is_one_line_with_single_spaces(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "  First line.\nSecond   line.\r\n\n\tThird. ")
    assert committed(repo) == message_of(
        "subject", MATCHES + "gov/a.txt", RATIONALE + "First line. Second line. Third.")


@pytest.mark.parametrize("sql", ["UPDATE audit_log SET rationale = NULL", "DELETE FROM audit_log"],
                         ids=["null-rationale", "no-audit-row"])
def test_a_receipt_without_a_rationale_is_written_as_none_recorded(repo, sql):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "Soon forgotten.")
    repo.audit(sql)
    assert committed(repo) == message_of("subject", MATCHES + "gov/a.txt", RATIONALE + "(none recorded)")


@pytest.mark.parametrize("name", ["gov/tab\there.txt", "star/new\nline.txt", "gov/bell\x07.txt", "gov/del\x7f.txt"],
                         ids=["tab", "newline", "bell", "delete"])
def test_a_path_with_a_control_character_is_written_as_a_json_string(repo, name):
    repo.put(name, "x\n")
    assert committed(repo) == message_of("subject", OUTSIDE + json.dumps(name))


def test_a_path_with_spaces_and_non_ascii_letters_is_written_as_it_is(repo):
    repo.write("gov/with space é.txt", "x\n", "A reason.")
    assert committed(repo) == message_of("subject", MATCHES + "gov/with space é.txt", RATIONALE + "A reason.")


def test_trailers_go_after_those_the_message_already_has(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    repo.git("add", "-A")
    assert repo.commit("-m", "subject\n\nBody text.\n\nCo-authored-by: Someone <someone@example.org>").returncode == 0
    assert repo.message() == (
        "subject\n\nBody text.\n\nCo-authored-by: Someone <someone@example.org>\n"
        + lines(MATCHES + "gov/a.txt", RATIONALE + "A reason."))


def test_comments_an_editor_leaves_are_stripped_and_the_record_stays(repo):
    repo.edit("gov/a.txt", "alpha", "ALPHA", "A reason.")
    repo.git("add", "-A")
    repo.put("message.txt", "subject\n\n# Please enter the commit message.\n")
    assert repo.commit("--cleanup=strip", "-F", "message.txt").returncode == 0
    assert repo.message() == message_of("subject", MATCHES + "gov/a.txt", RATIONALE + "A reason.")


def test_a_merge_commit_carries_the_record_of_what_it_brings_in(repo):
    trunk = repo.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    repo.git("checkout", "-q", "-b", "topic")
    repo.put("gov/b.txt", "from the topic\n")
    assert repo.commit_all("topic").returncode == 0
    repo.git("checkout", "-q", trunk)
    repo.put("other/o.txt", "on trunk\n")
    assert repo.commit_all("trunk").returncode == 0
    done = repo.run(["git", *IDENTITY, "merge", "-q", "--no-ff", "-m", "merge topic", "topic"])
    assert done.returncode == 0, done.stderr
    assert repo.message() == message_of("merge topic", OUTSIDE + "gov/b.txt")


# T7: the hook only records


def test_an_audit_database_that_cannot_be_read_gives_a_not_made_line_and_the_commit_is_made(repo):
    repo.put(".data/boundary_validator_audit.db", b"this is not a database")
    repo.put("gov/a.txt", "by hand\n")
    before = repo.head()
    done = repo.commit_all("change a")
    assert done.returncode == 0, done.stderr
    assert repo.head() != before
    [made] = [line for line in repo.message().splitlines() if line.startswith("Actuarii-")]
    assert made.startswith(NOT_MADE) and len(made) > len(NOT_MADE)
    assert repo.message().startswith("change a\n\n")


def test_an_invalid_project_configuration_gives_a_not_made_line_and_the_commit_is_made(repo):
    repo.put(".actuarii.json", "{")
    repo.put("gov/a.txt", "by hand\n")
    repo.git("add", "gov/a.txt")
    done = repo.commit("-m", "change a")
    assert done.returncode == 0, done.stderr
    [made] = [line for line in repo.message().splitlines() if line.startswith("Actuarii-")]
    assert made.startswith(NOT_MADE) and ".actuarii.json" in made


def test_a_missing_audit_database_is_no_error_but_no_recorded_writes(repo):
    assert not (repo.root / ".data").exists()
    repo.put("gov/a.txt", "by hand\n")
    assert committed(repo) == message_of("subject", OUTSIDE + "gov/a.txt")


@pytest.mark.parametrize("module", ["tools/project_config.py", "tools/audit/run_process.py",
                                    "tools/boundary_validator/hook_gate.py"])
def test_a_script_that_cannot_start_is_reported_on_stderr_and_the_commit_is_made_with_its_message_as_it_was(
        repo, module):
    repo.path(module).unlink()
    repo.put("other/o.txt", "changed\n")
    repo.git("add", "other/o.txt")
    done = repo.commit("-m", "other")
    assert done.returncode == 0, done.stderr
    assert "[commit_record] cannot start" in done.stderr
    assert "[commit_record] the record was not made (exit status 1); the commit goes on" in done.stderr
    assert repo.message() == "other\n"


def test_a_python_that_fails_is_reported_with_its_exit_status_and_the_commit_is_made(repo):
    interpreter = repo.interpreters / "python3"
    interpreter.unlink()
    interpreter.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    interpreter.chmod(0o755)
    repo.put("gov/a.txt", "by hand\n")
    done = repo.commit_all("change a")
    assert done.returncode == 0, done.stderr
    assert "[commit_record] the record was not made (exit status 3); the commit goes on" in done.stderr
    assert repo.message() == "change a\n"


@pytest.mark.parametrize("arguments", [(), ("one", "two")], ids=["none", "two"])
def test_the_script_exits_two_with_a_usage_line_unless_it_gets_exactly_one_path(repo, arguments):
    done = repo.run([sys.executable, str(repo.root / "tools" / "git" / "commit_record.py"), *arguments])
    assert (done.returncode, done.stdout) == (2, "")
    assert done.stderr.startswith("usage: ") and len(done.stderr.splitlines()) == 1


def test_a_commit_that_changes_no_governed_path_keeps_its_message_byte_for_byte(repo):
    repo.put("other/o.txt", "changed\n")
    repo.git("add", "-A")
    assert repo.commit("-m", "subject\n\nBody   with  spaces.\n\nAnd more.\n").returncode == 0
    assert repo.message() == "subject\n\nBody   with  spaces.\n\nAnd more.\n"


def test_an_empty_commit_keeps_its_message(repo):
    assert repo.commit("--allow-empty", "-m", "nothing").returncode == 0
    assert repo.message() == "nothing\n"


def test_an_empty_message_that_is_allowed_stays_empty(repo):
    repo.put("gov/a.txt", "by hand\n")
    repo.git("add", "-A")
    assert repo.commit("--allow-empty-message", "-m", "").returncode == 0
    assert repo.message() == ""


def abort_with(repo, *arguments, text=None):
    """A commit of a governed change whose message git takes for empty: git aborts it, and the hook adds nothing."""
    repo.put("gov/a.txt", "by hand\n")
    repo.git("add", "-A")
    if text is not None:
        repo.put("message.txt", text)
    before = repo.head()
    done = repo.commit(*arguments)
    assert done.returncode != 0
    assert "empty commit message" in done.stderr
    assert repo.head() == before
    assert "Actuarii-" not in (repo.root / ".git" / "COMMIT_EDITMSG").read_text(encoding="utf-8")


def test_a_message_that_holds_only_comments_is_left_alone_so_that_git_aborts_the_commit(repo):
    abort_with(repo, "--cleanup=strip", "-F", "message.txt", text="# Only a comment.\n# And another.\n")


def test_a_message_that_holds_only_whitespace_and_comments_is_left_alone_so_that_git_aborts_the_commit(repo):
    abort_with(repo, "--cleanup=strip", "-F", "message.txt", text="\n   \n# A comment.\n\n")


def test_an_editor_that_leaves_only_the_template_is_left_alone_so_that_git_aborts_the_commit(repo):
    abort_with(repo, "-e")


def test_a_verbose_commit_whose_editor_leaves_only_comments_above_the_scissors_and_a_diff_below_is_left_alone(repo):
    abort_with(repo, "-v")


def test_a_verbose_commit_gets_the_record_above_the_comments_and_the_diff_git_cuts_off(repo):
    repo.put("gov/a.txt", "by hand\n")
    repo.git("add", "-A")
    assert repo.commit("-v", editor=repo.subject_editor()).returncode == 0
    assert repo.message() == message_of("subject", OUTSIDE + "gov/a.txt")


def test_a_commit_edited_in_an_editor_gets_the_record_above_the_comments_git_strips(repo):
    repo.put("gov/a.txt", "by hand\n")
    repo.git("add", "-A")
    assert repo.commit(editor=repo.subject_editor()).returncode == 0
    assert repo.message() == message_of("subject", OUTSIDE + "gov/a.txt")


# T5, T9: the hook script itself


def test_the_hook_is_a_posix_sh_script_that_runs_the_record_at_the_top_of_the_repository_and_always_exits_zero():
    text = HOOK.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert "git rev-parse --show-toplevel" in text
    assert 'python3 "$top/tools/git/commit_record.py" "$1"' in text
    assert "[commit_record] the record was not made (exit status $status); the commit goes on" in text
    assert text.endswith("exit 0\n")
    assert "exit 1" not in text


def test_the_hook_has_the_mode_the_pre_commit_has_in_the_tree():
    assert stat.S_IMODE(HOOK.stat().st_mode) == stat.S_IMODE(PRE_COMMIT.stat().st_mode)
