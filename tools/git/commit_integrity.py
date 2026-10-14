"""Git pre-commit check: a staged governed path must equal the file on disk.

With the Bash sandbox on, the disk of a governed path is written only through the write gate (Edit/Write with a
receipt) or by the person. The index is outside both: a `git checkout <commit> -- <path>` that fails to write the
file has already staged the old content, and `git hash-object -w` with `git update-index` stages anything. This
check refuses the commit when a path it stages is governed (tools/project_config) and its index side, absent or
mode and blob, is not what is on disk: the blob is the one git would store for the file, the filters of the
repository applied, and the mode is 100755 when the owner may execute the file, else 100644. A symbolic link or
any other file that is not a regular file at such a path is refused. A governed file is committed whole: a partial
staging (`git add -p`) differs from the disk and is refused. Governed or not, a staged path must also be spelled as the
disk spells it: every component that exists on disk must be listed in its directory under exactly the staged name,
so that a case variant (TESTS/x.py for tests/x.py on a case-insensitive filesystem) cannot dodge a governed path.

tools/git/pre-commit runs it; the person copies that script to .git/hooks/pre-commit, which the sandbox protects.
Every git command starts through tools.audit.run_process and inherits the environment, so GIT_INDEX_FILE (set by
`git commit -a` and `git commit <paths>`) and GIT_DIR are honoured. Exit 0 only when every staged governed path
matches, including when none is staged; anything else exits 1 with lines starting [commit_integrity]: a mismatch,
an invalid project configuration, a git command that fails, output that cannot be parsed, any other error.
`--no-verify` and the internal commands of git skip hooks, which is a declared limit.

Standard library plus tools.project_config and tools.audit.run_process, importable by a Python 3.9 interpreter,
because git may run it under the system one.
"""
from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PREFIX = "[commit_integrity]"
RAW_ENTRY = re.compile(r":([0-7]{6}) ([0-7]{6}) ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) ([A-Z])")
STAGED_STATUSES = ("A", "M", "D", "T")
ABSENT_MODE = "000000"
WAY_OUT = (
    f"{PREFIX} write the file through the gate and stage the whole file, or run `git restore --staged <path>`"
)

try:
    if str(REPO_ROOT) in sys.path:
        import tools
    else:
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import tools
        finally:
            sys.path.remove(str(REPO_ROOT))
    from tools import project_config
    from tools.audit import run_process
except Exception as exc:
    sys.stderr.write(f"{PREFIX} cannot start ({type(exc).__name__}: {exc}); the commit is refused\n")
    sys.exit(1)


class CheckError(Exception):
    """git did not answer as expected; the message says what."""


def _git(cwd: str | None, *args: str, stdin: str = "") -> str:
    done = run_process.run(["git", *args], cwd=cwd, stdin=stdin)
    if done.returncode != 0:
        raise CheckError(f"git {' '.join(args)} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def _base(root: str) -> str:
    """What the commit is compared with: HEAD, or the empty tree before the first commit."""
    probe = run_process.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=root)
    if probe.returncode == 0:
        return "HEAD"
    if probe.returncode == 1 and not probe.stderr.strip():
        return _git(root, "hash-object", "-t", "tree", "--stdin").rstrip("\n")
    raise CheckError(f"git rev-parse --verify --quiet HEAD exited {probe.returncode}: {probe.stderr.strip()}")


def _staged(root: str) -> list:
    """(path, index side) of every path the commit stages, a rename counting as a deletion and an addition;
    the index side is None when the path is absent and (mode, blob) when it is there."""
    output = _git(
        root, "diff-index", "--cached", "--raw", "--no-renames", "--no-abbrev", "-z", "--ignore-submodules=none",
        _base(root),
    )
    fields = output.split("\0")
    if fields.pop() != "" or len(fields) % 2:
        raise CheckError("cannot parse the output of git diff-index")
    staged = []
    for meta, path in zip(fields[0::2], fields[1::2]):
        found = RAW_ENTRY.fullmatch(meta)
        if found is None or found.group(5) not in STAGED_STATUSES:
            raise CheckError(f"cannot parse the output of git diff-index for {path!r}: {meta!r}")
        mode, blob = found.group(2), found.group(4)
        staged.append((path, None if mode == ABSENT_MODE else (mode, blob)))
    return staged


def _difference(root: str, rel: str, index: tuple | None) -> str | None:
    """What differs between the index side of `rel` and the disk, or None when they are the same."""
    try:
        info = os.lstat(os.path.join(root, rel))
    except (FileNotFoundError, NotADirectoryError):
        return None if index is None else "a staged file that is not on disk"
    if not stat.S_ISREG(info.st_mode):
        return "not a regular file"
    if index is None:
        return "a staged deletion of a file that is still on disk"
    if _git(root, "hash-object", "--", rel).rstrip("\n") != index[1]:
        return "the staged content differs from the file on disk"
    if ("100755" if info.st_mode & stat.S_IXUSR else "100644") != index[0]:
        return "the staged mode differs from the file on disk"
    return None


def _misspelling(root: str, rel: str, listings: dict) -> str | None:
    """Why `rel` is not spelled as the disk spells it, or None. The components are walked from the root while they
    exist on disk (os.lstat of the staged spelling succeeds); each must be listed in its directory under exactly
    that name. A path that is new on disk ends the walk and passes. An error while listing propagates."""
    parts = rel.split("/")
    for depth, part in enumerate(parts):
        directory = os.path.join(root, *parts[:depth])
        try:
            here = os.lstat(os.path.join(directory, part))
        except (FileNotFoundError, NotADirectoryError):
            return None
        if directory not in listings:
            listings[directory] = os.listdir(directory)
        names = listings[directory]
        if part in names:
            continue
        for name in names:
            if name.casefold() == part.casefold() or os.path.samestat(here, os.lstat(os.path.join(directory, name))):
                return f"the staged spelling differs from the name on disk: '{part}' is listed as '{name}'"
        return f"the staged spelling differs from the name on disk: '{part}' exists but no listed name matches it"
    return None


def check(root: str) -> list:
    """One line for every staged path spelled otherwise than the disk spells it and for every staged governed path
    that differs from the disk; raises ConfigError while the project configuration is invalid and CheckError when
    git does not answer as expected."""
    problems = []
    listings: dict = {}
    for rel, index in _staged(root):
        misspelled = _misspelling(root, rel, listings)
        if misspelled is not None:
            problems.append(f"{PREFIX} {rel}: {misspelled}")
            continue
        governed = project_config.governance(rel)
        if governed is None:
            continue
        what = _difference(root, rel, index)
        if what is not None:
            problems.append(f"{PREFIX} {rel}: {what} (rule: {governed.rule}; source: {governed.source})")
    return problems


def _refuse(lines: list) -> int:
    sys.stderr.write("\n".join(lines) + "\n")
    return 1


def main() -> int:
    try:
        problems = check(_git(None, "rev-parse", "--show-toplevel").rstrip("\n"))
    except project_config.ConfigError as exc:
        return _refuse([f"{PREFIX} {exc}; the governed paths cannot be told, so the commit is refused"])
    except CheckError as exc:
        return _refuse([f"{PREFIX} cannot verify the index: {exc}; the commit is refused"])
    except Exception as exc:
        return _refuse([f"{PREFIX} cannot verify the index ({type(exc).__name__}: {exc}); the commit is refused"])
    return _refuse([*problems, WAY_OUT]) if problems else 0


if __name__ == "__main__":
    sys.exit(main())
