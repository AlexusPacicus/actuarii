"""Python gate (AGENTS 2.5): the PATH shim tools/bin/python3 and the session hook that puts it
first on the PATH of every Bash call. Static properties of the files, then their behaviour: each
runs from a temporary git repository against stub interpreters, through tools.audit.run_process.

Normative: AGENTS.md 2.5, 6.2
"""
import os
import shlex
import shutil
from collections import namedtuple
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.audit.run_process import run

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


SESSION_HOOK = SCRIPTS[1]

# A stand-in interpreter: it records which one started, then reports its argv, the environment
# variables that matter here and its stdin, and exits with $STUB_EXIT.
STUB = r"""#!/bin/sh
echo {name} > '{marker}'
echo 'STUB {name}'
for argument in "$@"; do printf 'ARG %s\n' "$argument"; done
/usr/bin/env | while IFS= read -r line; do
  case $line in PATH=*|PYTHON*|PYENV*|GIT_*) printf 'ENV %s\n' "$line" ;; esac
done
echo STDIN
/bin/cat
exit ${{STUB_EXIT:-0}}
"""

Ran = namedtuple("Ran", "returncode stdout stderr stub args env stdin")

SHELLS = [
    pytest.param(
        name,
        id=name or "shebang",
        marks=pytest.mark.skipif(name is not None and shutil.which(name) is None, reason=f"{name} is not installed"),
    )
    for name in (None, "bash", "dash")
]


class Gate:
    """A temporary world for the shim: git repositories holding copies of it, stub interpreters that
    report what they were given, and a git that no user configuration reaches."""

    def __init__(self, base):
        self.base = base
        self.marker = base / "marker"
        self.stubs = base / "stubs"
        self.gitbin = base / "gitbin"
        self.base_env = {"HOME": str(base), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        for name in ("python3", "python", "python3.11"):
            self.stub(self.stubs, name)
        self.stub(base / "cwdstub", "python3", label="cwd")
        self.gitbin.mkdir()
        wrapper = self.gitbin / "git"
        wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(shutil.which("git") or "git")} "$@"\n')
        wrapper.chmod(0o755)
        self.repo = self.make_repo("repo", ["tools/x.py", "tools/sub/s.py", "traianus/y.py", "tests/z.py", "root.py"])
        self.shim_dir = self.repo / "tools" / "bin"
        self.write("tools/untracked.py")
        self.write("tools/untracked2.py")
        (base / "binlink").symlink_to(self.shim_dir)
        self.second = self.make_repo("second", ["tools/evil.py"], shim=False)
        self.decoy = self.make_repo("decoy", ["tools/untracked2.py"], shim=False)

    def stub(self, directory, name, label=None):
        directory.mkdir(exist_ok=True)
        (directory / name).write_text(STUB.format(name=label or name, marker=self.marker))
        (directory / name).chmod(0o755)

    def write(self, relative, root=None, text="print(1)\n"):
        path = (root or self.repo) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def git(self, *args, cwd=None):
        done = run(
            [str(self.gitbin / "git"), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=cwd or self.repo,
            env={**self.base_env, "PATH": str(self.gitbin)},
        )
        assert done.returncode == 0, done.stderr

    def commit(self, relative):
        self.git("add", "--", relative)
        self.git("commit", "-q", "-m", "m", "--", relative)

    def copy_shim(self, root):
        target = root / "tools" / "bin"
        target.mkdir(parents=True)
        shutil.copy2(BIN / "python3", target / "python3")
        for name in ("python", "python3.11"):
            (target / name).symlink_to("python3")

    def make_repo(self, name, scripts, shim=True):
        root = self.base / name
        root.mkdir()
        for script in scripts:
            self.write(script, root)
        if shim:
            self.copy_shim(root)
        self.git("init", "-q", cwd=root)
        self.git("add", "-A", cwd=root)
        self.git("commit", "-q", "-m", "init", cwd=root)
        return root

    def path(self, first):
        return f"{first}:{self.stubs}:{self.gitbin}"

    def shim(self, *args, at=None, cwd=None, name="python3", shell=None, path=None, env=None, stdin=""):
        root = at or self.repo
        target = root / "tools" / "bin" / name
        argv = [shutil.which(shell), str(target), *args] if shell else [str(target), *args]
        environment = {**self.base_env, "PATH": self.path(target.parent) if path is None else path, **(env or {})}
        self.marker.unlink(missing_ok=True)
        done = run(argv, cwd=cwd or root, env=environment, stdin=stdin, timeout=10)
        if not self.marker.exists():
            return Ran(done.returncode, done.stdout, done.stderr, None, [], {}, "")
        header, _, piped = done.stdout.partition("STDIN\n")
        lines = header.splitlines()
        return Ran(
            done.returncode,
            done.stdout,
            done.stderr,
            self.marker.read_text().strip(),
            [line[4:] for line in lines if line.startswith("ARG ")],
            dict(line[4:].split("=", 1) for line in lines if line.startswith("ENV ")),
            piped,
        )


@pytest.fixture(scope="module")
def gate(tmp_path_factory):
    return Gate(tmp_path_factory.mktemp("gate").resolve())


def assert_gate_denies(ran):
    assert ran.returncode == 126
    assert ran.stdout == ""
    assert ran.stderr.startswith("python gate:")
    assert ran.stderr.count("\n") == 1
    assert ran.stub is None


# T1: a committed script runs, its argv, stdin and status untouched


@pytest.mark.parametrize("cwd, script", [
    pytest.param(".", "tools/x.py", id="tools-relative-from-root"),
    pytest.param(".", "@tools/x.py", id="tools-absolute-from-root"),
    pytest.param(".", "traianus/y.py", id="traianus-relative-from-root"),
    pytest.param(".", "@traianus/y.py", id="traianus-absolute-from-root"),
    pytest.param("tools/sub", "s.py", id="bare-name-from-a-subdirectory"),
    pytest.param("tools/sub", "../x.py", id="parent-relative-from-a-subdirectory"),
    pytest.param("..", "@tools/sub/s.py", id="absolute-from-outside-the-repository"),
])
def test_permits_a_committed_script_from_any_cwd(gate, cwd, script):
    given = str(gate.repo / script[1:]) if script.startswith("@") else script
    ran = gate.shim(given, cwd=gate.repo / cwd)
    assert (ran.returncode, ran.stub, ran.args, ran.stderr) == (0, "python3", [given], "")


def test_hands_the_interpreter_argv_stdin_and_status_unchanged(gate):
    ran = gate.shim("-u", "tools/x.py", "a", "b c", "", "-", stdin="in\nput\n", env={"STUB_EXIT": "7"})
    assert ran.returncode == 7
    assert ran.args == ["-u", "tools/x.py", "a", "b c", "", "-"]
    assert ran.stdin == "in\nput\n"
    assert ran.stdout.startswith("STUB python3\n") and ran.stderr == ""


@pytest.mark.parametrize("name", ["python", "python3.11"])
def test_the_other_names_run_the_stub_of_their_own_name(gate, name):
    ran = gate.shim("tools/x.py", name=name)
    assert (ran.returncode, ran.stub) == (0, name)
    assert ran.stdout.startswith(f"STUB {name}\n")


CORE = [
    pytest.param(["tools/x.py"], 0, id="committed-script"),
    pytest.param(["--version"], 0, id="version"),
    pytest.param(["-c", "x"], 126, id="inline-code"),
    pytest.param(["-m", "pytest"], 126, id="module"),
    pytest.param(["-"], 126, id="lone-dash"),
]


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("args, status", CORE)
def test_the_core_matrix_holds_under_each_shell(gate, shell, args, status):
    ran = gate.shim(*args, shell=shell)
    if status == 126:
        assert_gate_denies(ran)
    else:
        assert (ran.returncode, ran.stub, ran.args) == (0, "python3", args)


# T2: the options that may precede a script

OPTIONS = ["-u", "-B", "-OO", "-O", "-q", "-s", "-S", "-E", "-I"]


@pytest.mark.parametrize("option", ["--version", "-V", "-VV"])
def test_permits_a_version_option_as_the_sole_argument(gate, option):
    ran = gate.shim(option)
    assert (ran.returncode, ran.stub, ran.args) == (0, "python3", [option])


@pytest.mark.parametrize("option", OPTIONS)
def test_permits_each_option_of_the_closed_set_before_a_script(gate, option):
    ran = gate.shim(option, "tools/x.py")
    assert (ran.returncode, ran.stub, ran.args) == (0, "python3", [option, "tools/x.py"])


def test_permits_several_options_in_a_row_before_a_script(gate):
    ran = gate.shim(*OPTIONS, "tools/x.py")
    assert (ran.returncode, ran.args) == (0, [*OPTIONS, "tools/x.py"])


def test_never_reads_the_arguments_after_the_script(gate):
    after = ["-c", "-m", "-", "--version", "-i"]
    ran = gate.shim("tools/x.py", *after)
    assert (ran.returncode, ran.args) == (0, ["tools/x.py", *after])


# T3: everything else is denied before an interpreter starts


@pytest.mark.parametrize("args", [
    pytest.param(["-c", "x"], id="inline-code"),
    pytest.param(["-cx"], id="inline-code-attached"),
    pytest.param(["-uc", "x"], id="inline-code-in-a-cluster"),
    pytest.param(["-Bm", "x"], id="module-in-a-cluster"),
    pytest.param(["-m", "pytest"], id="module"),
    pytest.param(["-mpytest"], id="module-attached"),
    pytest.param(["-"], id="lone-dash"),
    pytest.param(["-u", "-"], id="option-then-lone-dash"),
    pytest.param(["-i"], id="interactive"),
    pytest.param(["-i", "tools/x.py"], id="interactive-before-a-script"),
    pytest.param(["-c", "tools/x.py"], id="inline-code-that-names-a-script"),
    pytest.param(["-m", "tools/x.py"], id="module-that-names-a-script"),
    pytest.param([], id="no-arguments"),
    pytest.param(["--version", "extra"], id="version-with-an-argument"),
    pytest.param(["--"], id="double-dash"),
    pytest.param(["-W", "ignore", "tools/x.py"], id="warning-option"),
    pytest.param(["-X", "importtime", "tools/x.py"], id="x-option"),
    pytest.param(["--unknown", "tools/x.py"], id="unknown-long-option"),
    pytest.param(["-u"], id="options-without-a-script"),
    pytest.param([""], id="empty-string"),
    pytest.param(["/dev/stdin"], id="dev-stdin"),
    pytest.param(["/dev/fd/0"], id="dev-fd"),
])
def test_denies_argv_that_is_not_a_committed_script(gate, args):
    assert_gate_denies(gate.shim(*args))


@pytest.mark.parametrize("args", [
    pytest.param(["-c\nx"], id="newline-in-an-option"),
    pytest.param(["tools/x.py\nsecond"], id="newline-in-the-script-name"),
    pytest.param(["\n"], id="only-a-newline"),
])
def test_a_newline_in_an_argument_does_not_add_a_stderr_line(gate, args):
    assert_gate_denies(gate.shim(*args))


@pytest.mark.parametrize("name", ["-c", "-m", "-"])
def test_a_committed_file_named_like_an_option_is_not_taken_for_a_script(gate, name):
    gate.write(f"tools/{name}")
    gate.commit(f"tools/{name}")
    assert_gate_denies(gate.shim(name, "x", cwd=gate.repo / "tools"))


# T4: the identity of the script


def staged_only(gate):
    gate.write("tools/staged.py")
    gate.git("add", "--", "tools/staged.py")
    return "tools/staged.py", None


def link_to_a_committed_file(gate):
    (gate.repo / "tools" / "link.py").symlink_to("x.py")
    return "tools/link.py", None


def committed_link(gate):
    (gate.repo / "tools" / "committed_link.py").symlink_to("x.py")
    gate.commit("tools/committed_link.py")
    return "tools/committed_link.py", None


def through_a_link_outside_the_repository(gate):
    outside = gate.base / "outside"
    outside.mkdir(exist_ok=True)
    gate.write("o.py", outside)
    (gate.repo / "tools" / "outlink").symlink_to(outside)
    return "tools/outlink/o.py", None


def committed_then_deleted(gate):
    gate.write("tools/gone.py")
    gate.commit("tools/gone.py")
    (gate.repo / "tools" / "gone.py").unlink()
    return "tools/gone.py", None


NOT_A_COMMITTED_SCRIPT = {
    "untracked": lambda gate: ("tools/untracked.py", None),
    "staged-not-committed": staged_only,
    "committed-in-tests": lambda gate: ("tests/z.py", None),
    "committed-in-the-root": lambda gate: ("root.py", None),
    "dotdot-into-tests": lambda gate: ("tools/../tests/z.py", None),
    "symlink-to-a-committed-file": link_to_a_committed_file,
    "committed-symlink": committed_link,
    "through-a-symlinked-directory-outside": through_a_link_outside_the_repository,
    "nonexistent": lambda gate: ("tools/nonexistent.py", None),
    "directory": lambda gate: ("tools/sub", None),
    "tools-itself": lambda gate: ("tools", None),
    "committed-then-deleted": committed_then_deleted,
    "second-repository-from-the-cwd-of-the-shim": lambda gate: (str(gate.second / "tools" / "evil.py"), None),
    "second-repository-from-its-own-cwd": lambda gate: (str(gate.second / "tools" / "evil.py"), gate.second),
}


@pytest.mark.parametrize("scenario", NOT_A_COMMITTED_SCRIPT.values(), ids=list(NOT_A_COMMITTED_SCRIPT))
def test_denies_a_script_that_is_not_a_committed_file_of_this_repository(gate, scenario):
    script, cwd = scenario(gate)
    assert_gate_denies(gate.shim(script, cwd=cwd))


def test_permits_a_committed_script_edited_in_the_working_tree(gate):
    """Declared limit: the gate binds the identity of the script, not its content."""
    path = gate.write("tools/edited.py")
    gate.commit("tools/edited.py")
    path.write_text("print('edited after the commit')\n")
    ran = gate.shim("tools/edited.py")
    assert (ran.returncode, ran.stub) == (0, "python3")


# T5: the caller's git variables and the state of the repository


@pytest.mark.parametrize("variables", [
    pytest.param(["GIT_DIR"], id="git-dir"),
    pytest.param(["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"], id="git-dir-work-tree-and-index"),
])
def test_git_variables_cannot_redirect_the_check_to_a_decoy_repository(gate, variables):
    values = {
        "GIT_DIR": str(gate.decoy / ".git"),
        "GIT_WORK_TREE": str(gate.decoy),
        "GIT_INDEX_FILE": str(gate.decoy / ".git" / "index"),
    }
    assert_gate_denies(gate.shim("tools/untracked2.py", env={key: values[key] for key in variables}))


def test_git_dir_alone_does_not_stop_a_committed_script(gate):
    ran = gate.shim("tools/x.py", env={"GIT_DIR": str(gate.decoy / ".git")})
    assert (ran.returncode, ran.stub) == (0, "python3")


def test_denies_a_copy_of_the_shim_outside_a_work_tree(gate):
    root = gate.base / "plain"
    gate.copy_shim(root)
    gate.write("tools/x.py", root)
    assert_gate_denies(gate.shim("tools/x.py", at=root))


def test_denies_a_copy_of_the_shim_in_a_repository_without_a_commit(gate):
    root = gate.base / "uncommitted"
    gate.copy_shim(root)
    gate.write("tools/x.py", root)
    gate.git("init", "-q", cwd=root)
    gate.git("add", "-A", cwd=root)
    assert_gate_denies(gate.shim("tools/x.py", at=root))


# T6: the environment of the interpreter


def test_removes_the_python_variables_that_change_what_the_interpreter_loads(gate):
    dropped = {
        "PYTHONPATH": "/x",
        "PYTHONHOME": "/x",
        "PYTHONSTARTUP": "/x",
        "PYTHONINSPECT": "1",
        "PYTHONUSERBASE": "/x",
    }
    ran = gate.shim("tools/x.py", env=dropped)
    assert (ran.returncode, ran.stub) == (0, "python3")
    assert not set(dropped) & set(ran.env)


def test_keeps_the_variables_that_do_not_change_what_the_interpreter_loads(gate):
    kept = {
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYENV_VERSION": "3.11.6",
        "GIT_DIR": str(gate.repo / ".git"),
    }
    ran = gate.shim("tools/x.py", env=kept)
    assert (ran.returncode, ran.stub) == (0, "python3")
    assert {key: ran.env.get(key) for key in kept} == kept
    assert ran.env["PATH"] == gate.path(gate.shim_dir)


# T7: the real interpreter is found on the PATH, outside the directory of the shim

SPELLINGS_OF_THE_SHIM_DIRECTORY = {
    "plain": lambda gate: str(gate.shim_dir),
    "trailing-slash": lambda gate: f"{gate.shim_dir}/",
    "dotdot": lambda gate: f"{gate.shim_dir}/../bin",
    "symlink": lambda gate: str(gate.base / "binlink"),
}


@pytest.mark.parametrize(
    "spell", SPELLINGS_OF_THE_SHIM_DIRECTORY.values(), ids=list(SPELLINGS_OF_THE_SHIM_DIRECTORY)
)
def test_skips_its_own_directory_however_it_is_spelled_on_the_path(gate, spell):
    ran = gate.shim("tools/x.py", path=gate.path(spell(gate)))
    assert (ran.returncode, ran.stub) == (0, "python3")


@pytest.mark.parametrize("spell", [
    pytest.param(lambda gate: f":{gate.shim_dir}:{gate.stubs}:{gate.gitbin}", id="leading"),
    pytest.param(lambda gate: f"{gate.shim_dir}::{gate.stubs}:{gate.gitbin}", id="middle"),
])
def test_skips_an_empty_path_entry_instead_of_using_the_working_directory(gate, spell):
    ran = gate.shim("--version", cwd=gate.base / "cwdstub", path=spell(gate))
    assert (ran.returncode, ran.stub) == (0, "python3")


@pytest.mark.parametrize("args", [["--version"], ["tools/x.py"]], ids=["version", "script"])
def test_without_another_interpreter_on_the_path_answers_127(gate, args):
    ran = gate.shim(*args, path=f"{gate.shim_dir}:{gate.gitbin}")
    assert (ran.returncode, ran.stdout, ran.stderr) == (127, "", "python gate: no real python3 on PATH\n")
    assert ran.stub is None


# T8: the session hook

TREES = ["plain", "a tree with spaces", "it's a tree"]


def install_session_hook(root):
    hook = root / "tools" / "hooks" / SESSION_HOOK.name
    hook.parent.mkdir(parents=True)
    shutil.copy2(SESSION_HOOK, hook)
    shutil.copytree(BIN, root / "tools" / "bin", symlinks=True)
    return hook


def start_session(hook, env_file=None):
    env = {"PATH": "/usr/bin:/bin"}
    if env_file is not None:
        env["CLAUDE_ENV_FILE"] = str(env_file)
    return run([str(hook)], cwd=hook.parent, env=env)


@pytest.mark.parametrize("tree", TREES)
def test_session_hook_appends_one_line_that_puts_the_shim_of_its_tree_first(tmp_path, tree):
    hook = install_session_hook(tmp_path / tree)
    env_file = tmp_path / "env"
    env_file.write_text("export EARLIER=1\n")
    started = start_session(hook, env_file)
    assert (started.returncode, started.stdout, started.stderr) == (0, "", "")
    lines = env_file.read_text().splitlines()
    assert len(lines) == 2 and lines[0] == "export EARLIER=1"
    found = run(["/bin/sh", "-c", '. "$1" && command -v python3', "sh", str(env_file)], env={"PATH": "/usr/bin:/bin"})
    assert found.stdout == f"{(tmp_path / tree).resolve() / 'tools' / 'bin'}/python3\n"


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_session_hook_without_an_env_file_says_so_and_exits_0(tmp_path, value):
    ran = start_session(install_session_hook(tmp_path / "tree"), value)
    assert (ran.returncode, ran.stdout) == (0, "")
    assert ran.stderr.startswith("python gate:") and ran.stderr.count("\n") == 1


@pytest.mark.parametrize("target", ["directory", "file-in-a-missing-directory"])
def test_session_hook_whose_append_fails_exits_1_with_nothing_on_stdout(tmp_path, target):
    env_file = tmp_path if target == "directory" else tmp_path / "missing" / "env"
    ran = start_session(install_session_hook(tmp_path / "tree"), env_file)
    assert (ran.returncode, ran.stdout) == (1, "")
    assert ran.stderr.startswith("python gate:") and ran.stderr.count("\n") == 1


# T14: the helper that runs a process for these tests


def test_run_returns_the_status_and_both_streams_of_the_child():
    done = run(["/bin/sh", "-c", "echo out; echo err >&2; exit 3"])
    assert (done.returncode, done.stdout, done.stderr) == (3, "out\n", "err\n")
    with pytest.raises(FrozenInstanceError):
        done.returncode = 0


def test_run_feeds_stdin_as_utf8_text():
    assert run(["/bin/cat"], stdin="é\n").stdout == "é\n"


def test_run_uses_exactly_the_given_environment(monkeypatch):
    monkeypatch.setenv("RUN_PROCESS_PROBE", "1")
    given = run(["/usr/bin/env"], env={"ONLY": "1"}).stdout.splitlines()
    assert "ONLY=1" in given and "RUN_PROCESS_PROBE=1" not in given
    assert "RUN_PROCESS_PROBE=1" in run(["/usr/bin/env"]).stdout.splitlines()


def test_run_passes_an_argument_holding_shell_syntax_as_one_argument():
    argument = "a b; echo $HOME"
    assert run(["/usr/bin/printf", "%s|", argument]).stdout == argument + "|"


def test_run_runs_in_the_given_cwd(tmp_path):
    assert Path(run(["/bin/pwd"], cwd=tmp_path).stdout.strip()).resolve() == tmp_path.resolve()


def test_run_lets_a_timeout_propagate():
    with pytest.raises(Exception) as caught:
        run(["/bin/sleep", "5"], timeout=0.2)
    assert type(caught.value).__name__ == "TimeoutExpired"


# T15: the committed modes of the gate files


@pytest.mark.parametrize("path, mode", [
    ("tools/bin/python3", "100755"),
    ("tools/hooks/session_python_gate.sh", "100755"),
    ("tools/bin/python", "120000"),
    ("tools/bin/python3.11", "120000"),
])
def test_the_committed_mode_of_a_gate_file(path, mode):
    if run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT).stdout.strip() != "true":
        pytest.skip("not inside a git work tree")
    entry = run(["git", "ls-files", "-s", "--", path], cwd=ROOT).stdout.split()
    assert entry[:1] == [mode]
    if mode == "120000":
        assert run(["git", "cat-file", "-p", entry[1]], cwd=ROOT).stdout == "python3"
