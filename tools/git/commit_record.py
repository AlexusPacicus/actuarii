"""Git commit-msg record: the message of a commit says whether recorded writes lead to what the commit stores.

tools/git/commit-msg runs it with the path of the message file. For every path the commit stages that the project
configuration (tools/project_config) governs and whose content the commit changes, it appends one `Actuarii-Record`
trailer to the message:

* `matches: <path>` when the writes that the write gate recorded (tools/boundary_validator/hook_gate: record_write,
  read back with recorded_writes) lead from the content at HEAD (the empty tree before the first commit) to the
  committed content, followed by one `Actuarii-Rationale` trailer for each distinct rationale of their receipts,
  in the order they first appear;
* `changed outside the channel: <path>` otherwise, a deletion included.

The content of a side is the SHA-256 of the bytes of its blob, as the gate hashes what it reads and what it leaves. The
writes that lead from the start to the end are found in the order they were recorded: a write whose `before` is a
content already reached, and whose `after` is not, extends the chain. A write the gate allowed and that never happened
counts when the same content arrives another way; no time bound applies. A blob that is not valid UTF-8 gets a value
that no recorded write has, since the gate records only UTF-8 results. A change of mode alone, a path no rule governs
and a gitlink get no trailer.

It only records. Any error while the trailers are computed (an invalid project configuration, a git command that
fails, an audit database that cannot be read) becomes one `Actuarii-Record: not made: <reason>` trailer, a missing
audit database being no error but no recorded writes, and the script exits 0. When no path gets a trailer, or the
message is empty once cut at the scissors line and stripped of comments (git then aborts the commit, and a trailer
must not turn that into a commit), the message is not touched. When the trailers cannot be written it says so on
stderr, exits 1, and tools/git/commit-msg lets the commit go on. It exits 2 with a usage line unless it gets exactly the
path of the message file.

Every git command starts through tools.audit.run_process and inherits the environment, so GIT_INDEX_FILE (set by
`git commit -a` and `git commit <paths>`) and GIT_DIR are honoured. Standard library plus tools.project_config,
tools.audit.run_process and tools.boundary_validator.hook_gate, importable by a Python 3.9 interpreter, because git
may run it under the system one. `--no-verify` and the internal commands of git skip the hook, which is a declared limit.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PREFIX = "[commit_record]"
USAGE = "usage: commit_record.py <path of the commit message file>"
RECORD = "Actuarii-Record"
RATIONALE = "Actuarii-Rationale"
NO_RATIONALE = "(none recorded)"
RAW_ENTRY = re.compile(r":([0-7]{6}) ([0-7]{6}) ([0-9a-f]{40,64}) ([0-9a-f]{40,64}) ([A-Z])")
STATUSES = ("A", "M", "D", "T")
ABSENT_MODE = "000000"
GITLINK_MODE = "160000"
CONTROL = re.compile("[\x00-\x1f\x7f]")
SCISSORS = " ------------------------ >8 ------------------------"
TRAILER_OPTIONS = ("--in-place", "--where", "end", "--if-exists", "add", "--if-missing", "add", "--no-divider")

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
    from tools.boundary_validator import hook_gate
except Exception as exc:
    sys.stderr.write(f"{PREFIX} cannot start ({type(exc).__name__}: {exc})\n")
    sys.exit(1)


class RecordError(Exception):
    """git did not answer as expected; the message says what."""


def _git(cwd: str | None, *args: str, stdin: str = "") -> str:
    done = run_process.run(["git", *args], cwd=cwd, stdin=stdin)
    if done.returncode != 0:
        raise RecordError(f"git {' '.join(args)} exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def _one_line(exc: Exception) -> str:
    return " ".join(f"{type(exc).__name__}: {exc}".split())


def _base(root: str) -> str:
    """What the commit is compared with: HEAD, or the empty tree before the first commit."""
    probe = run_process.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=root)
    if probe.returncode == 0:
        return "HEAD"
    if probe.returncode == 1 and not probe.stderr.strip():
        return _git(root, "hash-object", "-t", "tree", "--stdin").rstrip("\n")
    raise RecordError(f"git rev-parse --verify --quiet HEAD exited {probe.returncode}: {probe.stderr.strip()}")


def _entries(root: str) -> list:
    """(path, old side, new side) of every path the commit stages, in git's order, a rename counting as a deletion and
    an addition; a side is None when the path is absent there and (mode, blob) when it is there."""
    output = _git(
        root, "diff-index", "--cached", "--raw", "--no-renames", "--no-abbrev", "-z", "--ignore-submodules=none",
        _base(root),
    )
    fields = output.split("\0")
    if fields.pop() != "" or len(fields) % 2:
        raise RecordError("cannot parse the output of git diff-index")
    entries = []
    for meta, path in zip(fields[0::2], fields[1::2]):
        found = RAW_ENTRY.fullmatch(meta)
        if found is None or found.group(5) not in STATUSES:
            raise RecordError(f"cannot parse the output of git diff-index for {path!r}: {meta!r}")
        old_mode, new_mode, old_blob, new_blob = found.group(1, 2, 3, 4)
        entries.append((
            path,
            None if old_mode == ABSENT_MODE else (old_mode, old_blob),
            None if new_mode == ABSENT_MODE else (new_mode, new_blob),
        ))
    return entries


def _content(root: str, side: tuple | None) -> str | None:
    """The SHA-256 of the bytes of the blob of `side`, None when the path is absent there. A blob that is not valid
    UTF-8 gets a value that is not a digest, so that no recorded write has it and two such blobs differ."""
    if side is None:
        return None
    try:
        text = _git(root, "cat-file", "blob", side[1])
    except UnicodeDecodeError:
        return f"blob {side[1]} is not valid UTF-8"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chain(path: str, start: str | None, end: str | None) -> list | None:
    """The recorded writes that lead from `start` to `end`, or None when none do (`end` None: a deletion)."""
    if end is None:
        return None
    writes = hook_gate.recorded_writes(path) if hook_gate.audit_trail_exists() else []
    reached: dict = {start: []}
    for write in writes:
        before, after, _rationales = write
        if before in reached and after not in reached:
            reached[after] = reached[before] + [write]
    return reached.get(end)


def _rationales(chain: list) -> list:
    """The distinct rationales of the writes of `chain`, in the order they first appear, on one line each."""
    found: list = []
    for _before, _after, rationales in chain:
        for rationale in rationales:
            text = NO_RATIONALE if rationale is None else " ".join(rationale.split())
            if text not in found:
                found.append(text)
    return found


def _lines(root: str) -> list:
    """The trailers of the commit, one line each, in the order of its entries; empty when no path gets one."""
    lines = []
    for path, old, new in _entries(root):
        if project_config.governance(path) is None:
            continue
        if GITLINK_MODE in [side[0] for side in (old, new) if side is not None]:
            continue
        if (None if old is None else old[1]) == (None if new is None else new[1]):
            continue
        shown = json.dumps(path) if CONTROL.search(path) else path
        chain = _chain(path, _content(root, old), _content(root, new))
        if chain is None:
            lines.append(f"{RECORD}: changed outside the channel: {shown}")
        else:
            lines.append(f"{RECORD}: matches: {shown}")
            lines.extend(f"{RATIONALE}: {text}" for text in _rationales(chain))
    return lines


def _empty(root: str | None, message: str) -> bool:
    """True when git takes the message for empty: nothing is left of it once it is cut before the scissors line and
    the lines git removes as comments are gone."""
    lines = message.split("\n")
    cut = next((index for index, line in enumerate(lines) if line.endswith(SCISSORS)), len(lines))
    return _git(root, "stripspace", "--strip-comments", stdin="\n".join(lines[:cut])).strip() == ""


def main(argv: list) -> int:
    if len(argv) != 1:
        sys.stderr.write(f"{USAGE}\n")
        return 2
    message = os.path.abspath(argv[0])
    root = None
    try:
        root = _git(None, "rev-parse", "--show-toplevel").rstrip("\n")
        lines = _lines(root)
    except Exception as exc:
        lines = [f"{RECORD}: not made: {_one_line(exc)}"]
    if not lines:
        return 0
    try:
        with open(message, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if not _empty(root, text):
            trailers = [argument for line in lines for argument in ("--trailer", line)]
            _git(root, "interpret-trailers", *TRAILER_OPTIONS, *trailers, message)
    except Exception as exc:
        sys.stderr.write(f"{PREFIX} cannot write the record into {message} ({_one_line(exc)})\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
