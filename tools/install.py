"""Installs the kit into an existing git repository without overwriting anything.

Run by the person, outside any session, from a clone of Actuarii:

    python3 tools/install.py [--dry-run] [--no-input] [--govern PATH]... [--install-pydantic] [--commit] <target>

The target must be the top level of a git working tree and not the clone itself; otherwise the exit status is 2
and nothing is written. It receives, from the clone's working tree:

* every file under tools/ (without __pycache__ and *.pyc) and under .claude/agents/ and .claude/skills/, with its
  bytes and executable bit, always as a regular file: the kit's own pre-commit hook refuses a link. A symbolic link
  of the clone is installed as the regular file it resolves to, with that file's bytes and executable bit, provided
  it resolves to a regular file inside those trees; any other link (dangling, in a loop, to a directory or to
  something outside them) is a problem of the clone: exit status 2, the path on stderr, nothing written;
* .actuarii.json, when absent, with an example configuration: the minimum governed paths (AGENTS.md, CLAUDE.md, .claude/**,
  .mcp.json and tools/**) followed by the extra paths of this run. One that exists is adopted when it equals the example in every
  key but governed_paths and its governed_paths are the minimum in its order followed by acceptable extra paths, without
  duplicates; it is merged, with the new extra paths appended, when this run adds some, and any other is a conflict;
* .claude/settings.json, with the clone's own `permissions` and `hooks`, `includeGitInstructions` false and a strict
  `sandbox`, merged into what is there: the clone's permission entries go after the target's own, once each, and a
  `defaultMode` already there stays; a bare `Bash` rule in the merged `ask` or `deny` is a warning, not a conflict;
* .mcp.json, with the clone's boundary-validator server, merged into what is there;
* the pre-commit hook and then the commit-msg hook, each where `git rev-parse --git-path hooks/<name>` says it goes,
  provided that is inside the target's own `.git` directory: a hooks path anywhere else (a global or escaping
  core.hooksPath, a hooks directory of the working tree, the git directory of a linked worktree or of a submodule) is a
  conflict. The two hooks follow the same rules: the kit's file with its bytes and mode 0755, skipped when the
  destination already holds exactly that, a conflict otherwise;
* a `.data/` line in .gitignore.

Everything is checked before the first write. A destination that already holds exactly what the kit needs is
skipped; anything else at a path the kit writes is a conflict. With any conflict the installer lists them all on
stderr, writes nothing and exits 1. `--dry-run` runs the same checks and prints the same plan and conflicts,
without writing. A write that fails midway exits 1 and names what was already written: there is no rollback.

The user's own settings are only read, to warn when they do not forbid unsandboxed commands; they are never written.

The report also says which interpreter the validator will start with (the `command` of the clone's server, looked up on
the installer's PATH from the target, never the Python shim) and whether it has the pydantic the kit is tested with. It
runs tools/check_pydantic.py with that interpreter, from the target and with no option, unless the interpreter lies
inside the target; it prints the pip command that would install the pin and runs it only on a yes or with --install-pydantic.

Three questions are asked in a real run and only there, each answered by one line of the standard input (the end of input
answers the default). A question is written on stderr only when the standard input is a terminal; the answers are read the
same way from a pipe, so that a script or a test can supply them:

* which paths to govern besides the minimum, before the plan is built and so before any write and before conflicts are looked
  for, unless --govern is given. It names the target, says that nothing is written until it is answered, names what is
  already governed and takes one path per line, each a file path or a directory followed by /**; an empty line or the
  end of input ends it. An answer the entry rules below refuse is explained on stderr, not taken, and reading goes on.
  Default: no other path;
* after the writes, whether to run `<executable> -m pip install pydantic==<pin>` for the interpreter the check named, when it
  has another pydantic or none and neither its executable nor its prefix lies inside the target; the report gives the result,
  and a new check when pip succeeded. Default: no;
* last, whether to commit what this run wrote in the working tree (not the git hooks) as "Install Actuarii": git add and git
  commit are limited to those paths, so that other staged or untracked files stay out, and the installed hooks run. Default: no.

--govern PATH (repeatable), --install-pydantic and --commit answer their question in advance. --no-input and --dry-run ask
nothing, and what no flag says is no; a dry run with --install-pydantic says what a real run would run. An entry, for --govern
and for an answer, is a plain path or a plain path followed by /**: not empty, relative (no leading / or ~), with no '..',
backslash, control character, * ? [ ] { }, trailing / or empty or '.' segment, and not starting with the segment .git or
.data; a plain path that names an existing directory of the target is refused (write it followed by /**). A refused --govern
exits 2 and nothing is written.

Exit status: 0 when all went well; 1 for a conflict, a write that fails, a pip that fails or a commit that fails (after the
report, except for a conflict or a write); 2 for a problem with the target or the clone and for a refused --govern.

Standard library only, plus tools.audit.run_process for the processes it starts (git and that interpreter). It imports
and runs under a Python 3.9 system interpreter.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shlex
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) in sys.path:
    import tools
else:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import tools
    finally:
        sys.path.remove(str(REPO_ROOT))

from tools.audit import run_process

PREFIX = "actuarii install: "
DRY_RUN_CLOSING = "dry run: nothing was written"
KIT_TREES = ("tools", ".claude/agents", ".claude/skills")
SERVER = "boundary-validator"
CONFIG_NAME = ".actuarii.json"
SETTINGS_NAME = ".claude/settings.json"
MCP_NAME = ".mcp.json"
GIT_HOOKS = ("pre-commit", "commit-msg")
GIT_HOOKS_SOURCE = "tools/git"
SHIM_SOURCE = "tools/bin/python3"
CHECK_SOURCE = "tools/check_pydantic.py"
CHECK_KEYS = {"executable", "prefix", "pydantic"}
CHECK_TIMEOUT = 60.0
PIP_TIMEOUT = 600.0
GIT_WRITE_TIMEOUT = 300.0
TIMED_OUT = run_process.subprocess.TimeoutExpired
PYTHON_PREFIX = "python: "
PIP_PREFIX = "pip: "
COMMIT_PREFIX = "commit: "
COMMIT_MESSAGE = "Install Actuarii"
COMMIT_QUESTION = f'commit the installed files now, as "{COMMIT_MESSAGE}"? [y/N] '
DIRECTORY_SUFFIX = "/**"
RESERVED_ROOTS = (".git", ".data")
WILDCARDS = "*?[]{}"
CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
PERMISSION_LISTS = ("allow", "deny", "ask")
PERMISSION_KEYS = ("defaultMode", *PERMISSION_LISTS)
BARE_BASH = ("Bash", "Bash(*)")
BARE_BASH_EFFECT = {"ask": "ask", "deny": "be denied"}
DATA_LINES = (b".data/", b"/.data/")
EXAMPLE_CONFIG = {
    "schema": "actuarii-config/1",
    "governed_paths": ["AGENTS.md", "CLAUDE.md", ".claude/**", ".mcp.json", "tools/**"],
    "python_script_dirs": ["."],
    "contract_registry": None,
    "review": None,
    "receipt_window_seconds": 900,
}
STRICT = {
    "enabled": True,
    "failIfUnavailable": True,
    "allowUnsandboxedCommands": False,
    "autoAllowBashIfSandboxed": False,
}
AUDIT_DB_ENTRY = "./.data/boundary_validator_audit.db"
CONFIG_ENTRY = "./" + CONFIG_NAME


class Problem(Exception):
    """Something that stops the installer; the message says what, on one line."""


@dataclass(frozen=True)
class Write:
    label: str
    path: Path
    content: Optional[bytes] = None
    mode: Optional[int] = None
    hook: bool = False


class Plan:
    def __init__(self, command: str) -> None:
        self.command = command
        self.writes: list[Write] = []
        self.skips: list[str] = []
        self.conflicts: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def conflict(self, label: str, why: str) -> None:
        if (label, why) not in self.conflicts:
            self.conflicts.append((label, why))


def git(arguments: list[str], cwd: Path, timeout: float = 30.0) -> str:
    try:
        done = run_process.run(["git", *arguments], cwd=cwd, timeout=timeout)
    except OSError as exc:
        raise Problem(f"cannot run git: {exc}") from exc
    if done.returncode != 0:
        raise Problem(f"git {' '.join(arguments)} exited {done.returncode}: {' '.join(done.stderr.split())}")
    return done.stdout.strip()


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Problem(f"cannot be read as JSON: {exc}") from exc


def dumps(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def check_target(argument: str) -> Path:
    target = Path(argument)
    if not target.exists():
        raise Problem(f"{argument}: no such directory")
    if not target.is_dir():
        raise Problem(f"{argument}: not a directory")
    target = target.resolve()
    if target == REPO_ROOT:
        raise Problem(f"{target} is the clone the installer runs from; give another repository")
    try:
        top = git(["rev-parse", "--show-toplevel"], target)
    except Problem as exc:
        raise Problem(f"{target} is not a git working tree ({exc})") from exc
    if Path(top).resolve() != target:
        raise Problem(f"{target} is not the top level of a git working tree (that is {top})")
    return target


def check_link(path: Path, roots: list[Path]) -> None:
    """A link of the clone is installed as the regular file it resolves to, which must lie inside the kit trees."""
    label = path.relative_to(REPO_ROOT).as_posix()
    try:
        resolved_mode = os.stat(path).st_mode
    except OSError as exc:
        raise Problem(f"{label}: a link of the clone that does not resolve ({exc.strerror})") from exc
    if not stat.S_ISREG(resolved_mode):
        raise Problem(f"{label}: a link of the clone to something that is not a regular file")
    if not any(root in Path(os.path.realpath(path)).parents for root in roots):
        raise Problem(f"{label}: a link of the clone that resolves outside the kit trees")


def kit_files() -> list[Path]:
    found = []
    roots = [Path(os.path.realpath(REPO_ROOT / tree)) for tree in KIT_TREES]
    for tree in KIT_TREES:
        if not (REPO_ROOT / tree).is_dir():
            raise Problem(f"the clone has no {tree} directory")
        for current, dirs, files in os.walk(REPO_ROOT / tree):
            dirs[:] = [name for name in dirs if name != "__pycache__"]
            for name in dirs + files:
                path = Path(current) / name
                if name.endswith(".pyc"):
                    continue
                if path.is_symlink():
                    check_link(path, roots)
                    found.append(path.relative_to(REPO_ROOT))
                elif path.is_file():
                    found.append(path.relative_to(REPO_ROOT))
    return sorted(found)


def pydantic_pin() -> str:
    found = re.search(r"pydantic==([0-9][0-9A-Za-z.]*)", (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if found is None:
        raise Problem("the clone's pyproject.toml does not pin pydantic")
    return found.group(1)


def clone_json(name: str) -> object:
    try:
        return load_json(REPO_ROOT / name)
    except Problem as exc:
        raise Problem(f"the clone's {name} {exc}") from exc


def clone_permissions(permissions: object) -> dict:
    where = f"the clone's {SETTINGS_NAME} permissions"
    if not isinstance(permissions, dict):
        raise Problem(f"{where} is not an object")
    for key in PERMISSION_LISTS:
        entries = permissions.get(key)
        if not isinstance(entries, list) or not all(isinstance(entry, str) for entry in entries):
            raise Problem(f"{where}.{key} is not a list of strings")
    if not isinstance(permissions.get("defaultMode"), str):
        raise Problem(f"{where}.defaultMode is not a string")
    return permissions


def clone_kit_settings() -> tuple[dict, dict, dict]:
    """The permissions and hooks of the clone's settings and its validator server, in the shape the merge needs."""
    try:
        settings = clone_json(SETTINGS_NAME)
        permissions, hooks = settings["permissions"], settings["hooks"]
        server = clone_json(MCP_NAME)["mcpServers"][SERVER]
        command = server["command"]
    except (KeyError, TypeError) as exc:
        raise Problem(f"the clone's {SETTINGS_NAME} or {MCP_NAME} lacks what the kit installs ({exc!r})") from exc
    if not isinstance(command, str) or not command:
        raise Problem(f"the clone's {MCP_NAME} {SERVER} command is not a non-empty string")
    return clone_permissions(permissions), hooks, server


def deny_write_entries(extras: list[str]) -> list[str]:
    entries = {"./" + path.removesuffix(DIRECTORY_SUFFIX) for path in [*EXAMPLE_CONFIG["governed_paths"], *extras]}
    return sorted(entries | {CONFIG_ENTRY, AUDIT_DB_ENTRY})


def plain_path(entry: str) -> str:
    """The path of an entry, a plain path or a plain path followed by /**; raises Problem with the reason when it is refused."""
    plain = entry.removesuffix(DIRECTORY_SUFFIX)
    if not plain:
        raise Problem("the path is empty")
    if plain.startswith(("/", "~")):
        raise Problem("the path must not start with / or ~; give it relative to the repository")
    if ".." in plain:
        raise Problem("the path must not hold '..'")
    if "\\" in plain:
        raise Problem("the path must not hold a backslash")
    if CONTROL_CHARACTER.search(plain):
        raise Problem("the path must not hold a control character")
    if any(char in WILDCARDS for char in plain):
        raise Problem(f"the path must not hold any of * ? [ ] {{ }}; a directory is written followed by {DIRECTORY_SUFFIX}")
    if plain.endswith("/"):
        raise Problem(f"the path must not end with /; a directory is written followed by {DIRECTORY_SUFFIX}")
    segments = plain.split("/")
    if any(segment in ("", ".") for segment in segments):
        raise Problem("the path must not have an empty or '.' segment")
    if segments[0] in RESERVED_ROOTS:
        raise Problem("the path must not start with .git or .data: the git directory and the audit trail are not governed paths")
    return plain


def check_entry(entry: str, target: Path) -> None:
    """Raises Problem with the reason when the entry cannot be governed in the target."""
    if plain_path(entry) == entry and os.path.isdir(target / entry):
        raise Problem(f"{entry} names a directory of the target; write it as {entry}{DIRECTORY_SUFFIX} to govern what is under it")


def check_govern(entries: list[str], target: Path) -> list[str]:
    for entry in entries:
        try:
            check_entry(entry, target)
        except Problem as exc:
            raise Problem(f"--govern {entry!r}: {exc}") from exc
    return entries


def adopted_extras(existing: object) -> Optional[list[str]]:
    """The extra paths of an existing configuration the installer adopts, or None for any other. It is adopted when it equals the
    example in every key but governed_paths, whose value is the minimum in its order followed by entries the rules accept (the
    directory check aside), none twice."""
    if not isinstance(existing, dict) or set(existing) != set(EXAMPLE_CONFIG):
        return None
    if any(existing[key] != value for key, value in EXAMPLE_CONFIG.items() if key != "governed_paths"):
        return None
    minimum, paths = EXAMPLE_CONFIG["governed_paths"], existing["governed_paths"]
    if not isinstance(paths, list) or paths[:len(minimum)] != minimum:
        return None
    extras = paths[len(minimum):]
    if not all(isinstance(extra, str) for extra in extras) or len(set(paths)) != len(paths):
        return None
    try:
        for extra in extras:
            plain_path(extra)
    except Problem:
        return None
    return extras


def existing_extras(target: Path) -> list[str]:
    """The extra paths of the configuration the target holds when the installer adopts it; none otherwise (plan_config reports a conflict)."""
    destination = target / CONFIG_NAME
    try:
        extras = adopted_extras(load_json(destination)) if os.path.lexists(destination) else None
    except Problem:
        extras = None
    return extras or []


def extra_paths(held: list[str], given: list[str]) -> list[str]:
    """The extra paths already held, then the entries of this run that are not governed yet, each once, in order."""
    known = [*EXAMPLE_CONFIG["governed_paths"], *held]
    return [*held, *(entry for entry in dict.fromkeys(given) if entry not in known)]


def read_line(question: str) -> Optional[str]:
    """The next line of the standard input without its line end, or None at its end; a terminal also gets the question on stderr."""
    if question and sys.stdin.isatty():
        sys.stderr.write(question)
        sys.stderr.flush()
    line = sys.stdin.readline()
    return line.rstrip("\r\n") if line else None


def confirmed(question: str) -> bool:
    answer = read_line(question)
    return answer is not None and answer.strip().lower() in ("y", "yes")


def ask_paths(target: Path, held: list[str]) -> list[str]:
    """The paths the person gives, one per line, until an empty line or the end of input; a refused one is explained and not taken."""
    governed = ", ".join([*EXAMPLE_CONFIG["governed_paths"], *held])
    question = (f"{PREFIX}installing into {target}; nothing is written until you answer, and Ctrl-C stops here\n"
                f"{PREFIX}already governed: {governed}\n"
                f"{PREFIX}other paths to govern, one per line, each a file or a directory followed by {DIRECTORY_SUFFIX}; "
                "an empty line ends\n")
    answers: list[str] = []
    while True:
        line = read_line(question)
        question = ""
        answer = "" if line is None else line.strip()
        if not answer:
            return answers
        try:
            check_entry(answer, target)
        except Problem as exc:
            sys.stderr.write(f"{PREFIX}{answer!r} was not taken: {exc}\n")
        else:
            answers.append(answer)


def blocked(plan: Plan, target: Path, destination: Path) -> bool:
    """True, with the conflict recorded, when a directory on the way to the destination is not a real directory."""
    for ancestor in reversed(destination.parents):
        if target in ancestor.parents and os.path.lexists(ancestor) and (ancestor.is_symlink() or not ancestor.is_dir()):
            plan.conflict(ancestor.relative_to(target).as_posix(), "exists and is not a directory")
            return True
    return False


def plan_file(plan: Plan, label: str, destination: Path, content: bytes, mode: int, hook: bool = False) -> None:
    if not os.path.lexists(destination):
        plan.writes.append(Write(label, destination, content=content, mode=mode, hook=hook))
    elif destination.is_symlink() or not destination.is_file():
        plan.conflict(label, "exists and is not a regular file")
    else:
        try:
            existing = destination.read_bytes()
        except OSError as exc:
            plan.conflict(label, f"cannot be read: {exc}")
            return
        executable = bool(os.lstat(destination).st_mode & stat.S_IXUSR)
        if existing != content:
            plan.conflict(label, "exists with other content")
        elif executable != bool(mode & stat.S_IXUSR):
            plan.conflict(label, "exists with the same content and another executable bit")
        else:
            plan.skips.append(label)


def plan_kit(plan: Plan, target: Path) -> None:
    for relative in kit_files():
        label = relative.as_posix()
        source, destination = REPO_ROOT / relative, target / relative
        if blocked(plan, target, destination):
            continue
        executable = bool(os.stat(source).st_mode & stat.S_IXUSR)
        plan_file(plan, label, destination, source.read_bytes(), 0o755 if executable else 0o644)


def plan_config(plan: Plan, target: Path, extras: list[str]) -> None:
    destination = target / CONFIG_NAME
    governed = [*EXAMPLE_CONFIG["governed_paths"], *extras]
    if not os.path.lexists(destination):
        plan.writes.append(Write(CONFIG_NAME, destination, content=dumps({**EXAMPLE_CONFIG, "governed_paths": governed})))
        return
    try:
        existing = load_json(destination)
    except Problem as exc:
        plan.conflict(CONFIG_NAME, str(exc))
        return
    held = adopted_extras(existing)
    if held is None:
        plan.conflict(CONFIG_NAME, "exists and differs from the example configuration; the installer does not adopt another")
    elif held == extras:
        plan.skips.append(CONFIG_NAME)
    else:
        plan.writes.append(Write(CONFIG_NAME, destination, content=dumps({**existing, "governed_paths": governed})))


def merge_permissions(merged: dict, permissions: dict, problems: list[str]) -> None:
    """The clone's permissions into merged: its entries after the target's own, once each; a defaultMode already there stays."""
    if "permissions" not in merged:
        merged["permissions"] = copy.deepcopy(permissions)
        return
    current = merged["permissions"]
    if not isinstance(current, dict):
        problems.append("permissions is not an object")
        return
    for key in PERMISSION_KEYS:
        if key not in current:
            current[key] = copy.deepcopy(permissions[key])
        elif key in PERMISSION_LISTS and not isinstance(current[key], list):
            problems.append(f"permissions.{key} is not a list")
        elif key in PERMISSION_LISTS:
            current[key] += [entry for entry in dict.fromkeys(permissions[key]) if entry not in current[key]]


def merge_settings(existing: object, permissions: dict, hooks: dict, deny_entries: list[str]) -> tuple[object, list[str]]:
    if not isinstance(existing, dict):
        return existing, ["is not a JSON object"]
    problems = []
    merged = copy.deepcopy(existing)
    merge_permissions(merged, permissions, problems)
    if merged.get("disableAllHooks") is True:
        problems.append("disableAllHooks is true, so the kit's hooks would not run")
    current_hooks = merged.setdefault("hooks", {})
    if not isinstance(current_hooks, dict):
        problems.append("hooks is not an object")
    else:
        for event, groups in hooks.items():
            current = current_hooks.setdefault(event, [])
            if not isinstance(current, list):
                problems.append(f"hooks.{event} is not a list")
                continue
            current.extend([group for group in groups if group not in current])
    if "includeGitInstructions" not in merged:
        merged["includeGitInstructions"] = False
    elif merged["includeGitInstructions"] is not False:
        problems.append(
            f"includeGitInstructions is {json.dumps(merged['includeGitInstructions'])} and the kit needs false, "
            "since otherwise tools/audit/build_review_package.py --lock sets no review lock"
        )
    sandbox = merged.setdefault("sandbox", {})
    if not isinstance(sandbox, dict):
        problems.append("sandbox is not an object")
        return merged, problems
    for key, value in STRICT.items():
        if key not in sandbox:
            sandbox[key] = value
        elif sandbox[key] is not value:
            problems.append(f"sandbox.{key} is {json.dumps(sandbox[key])} and the kit needs {json.dumps(value)}")
    filesystem = sandbox.setdefault("filesystem", {})
    if not isinstance(filesystem, dict):
        problems.append("sandbox.filesystem is not an object")
        return merged, problems
    deny_write = filesystem.setdefault("denyWrite", [])
    if not isinstance(deny_write, list):
        problems.append("sandbox.filesystem.denyWrite is not a list")
        return merged, problems
    deny_write.extend([entry for entry in deny_entries if entry not in deny_write])
    return merged, problems


def bare_bash_warnings(merged: dict) -> list[str]:
    """One warning per bare Bash rule in the deny and ask lists of settings that merged without a problem."""
    return [
        f"{SETTINGS_NAME} permissions.{name} holds {json.dumps(entry)}: Claude Code evaluates deny, then ask, then allow, "
        f"so this entry makes every Bash command {BARE_BASH_EFFECT[name]} and no allow rule takes effect"
        for name in ("deny", "ask")
        for entry in merged["permissions"][name]
        if entry in BARE_BASH
    ]


def merge_mcp(existing: object, server: dict) -> tuple[object, list[str]]:
    if not isinstance(existing, dict):
        return existing, ["is not a JSON object"]
    merged = copy.deepcopy(existing)
    servers = merged.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return merged, ["mcpServers is not an object"]
    if SERVER not in servers:
        servers[SERVER] = server
    elif servers[SERVER] != server:
        return merged, [f"mcpServers.{SERVER} exists and differs from the kit's"]
    return merged, []


def plan_json(plan: Plan, target: Path, label: str, merge) -> None:
    """merge(existing) returns the merged value and the problems that make it a conflict; an absent file merges as {}."""
    destination = target / label
    if blocked(plan, target, destination):
        return
    present = os.path.lexists(destination)
    try:
        existing = load_json(destination) if present else {}
    except Problem as exc:
        plan.conflict(label, str(exc))
        return
    merged, problems = merge(existing)
    for problem in problems:
        plan.conflict(label, problem)
    if problems:
        return
    if present and merged == existing:
        plan.skips.append(label)
    else:
        plan.writes.append(Write(label, destination, content=dumps(merged)))


def hook_problem(target: Path, destination: Path) -> str:
    """Why the hook must not go to the destination, or an empty string when it may: only inside the target's own .git."""
    own = target / ".git"
    resolved = Path(os.path.realpath(destination.parent)) / destination.name
    own_git_directory = Path(os.path.realpath(git(["rev-parse", "--absolute-git-dir"], target))) == own
    if own_git_directory and own in resolved.parents:
        return ""
    hooks_path = git(["config", "--default", "", "--get", "core.hooksPath"], target)
    if hooks_path:
        cause = (f"core.hooksPath ({hooks_path}) puts the hooks there; unset it, "
                 "or wire the kit's git hooks into those hooks by hand")
    else:
        cause = (f"the git directory of the target is not {own} (a linked worktree, or a git directory elsewhere, "
                 "as in a submodule or --separate-git-dir), so its hooks belong to another repository; "
                 "install from the main working tree")
    return f"the hook would go to {resolved}, outside {own}: {cause}"


def plan_git_hook(plan: Plan, target: Path, name: str) -> None:
    shown = git(["rev-parse", "--git-path", f"hooks/{name}"], target)
    if not shown:
        raise Problem(f"git did not say where the {name} hook goes")
    destination = target / shown
    if blocked(plan, target, destination):
        return
    problem = hook_problem(target, destination)
    if problem:
        plan.conflict(shown, problem)
    else:
        plan_file(plan, shown, destination, (REPO_ROOT / GIT_HOOKS_SOURCE / name).read_bytes(), 0o755, hook=True)


def plan_gitignore(plan: Plan, target: Path) -> None:
    destination = target / ".gitignore"
    if not os.path.lexists(destination):
        plan.writes.append(Write(".gitignore", destination, content=DATA_LINES[0] + b"\n"))
        return
    try:
        existing = destination.read_bytes()
    except OSError as exc:
        plan.conflict(".gitignore", f"cannot be read: {exc}")
        return
    if any(line in DATA_LINES for line in existing.splitlines()):
        plan.skips.append(".gitignore")
        return
    separator = b"" if not existing or existing.endswith(b"\n") else b"\n"
    plan.writes.append(Write(".gitignore", destination, content=existing + separator + DATA_LINES[0] + b"\n"))


def build_plan(target: Path, extras: list[str]) -> Plan:
    permissions, hooks, server = clone_kit_settings()
    plan = Plan(server["command"])

    def merge_kit_settings(existing: object) -> tuple[object, list[str]]:
        merged, problems = merge_settings(existing, permissions, hooks, deny_write_entries(extras))
        if not problems:
            plan.warnings.extend(bare_bash_warnings(merged))
        return merged, problems

    plan_kit(plan, target)
    plan_config(plan, target, extras)
    plan_json(plan, target, SETTINGS_NAME, merge_kit_settings)
    plan_json(plan, target, MCP_NAME, lambda existing: merge_mcp(existing, server))
    for name in GIT_HOOKS:
        plan_git_hook(plan, target, name)
    plan_gitignore(plan, target)
    return plan


def apply(write: Write) -> None:
    write.path.parent.mkdir(parents=True, exist_ok=True)
    write.path.write_bytes(write.content)
    if write.mode is not None:
        os.chmod(write.path, write.mode)


def unsandboxed_commands_gap() -> str:
    """Why the user's own settings do not forbid unsandboxed commands, or an empty string when they do."""
    try:
        path = Path.home() / ".claude" / "settings.json"
    except RuntimeError as exc:
        return f"the home directory is unknown ({exc})"
    try:
        settings = load_json(path)
    except Problem as exc:
        return f"{path} {exc}"
    sandbox = settings.get("sandbox") if isinstance(settings, dict) else None
    if isinstance(sandbox, dict) and sandbox.get("allowUnsandboxedCommands") is False:
        return ""
    return f"{path} does not set sandbox.allowUnsandboxedCommands to false"


class CannotTell(Exception):
    """The installer could not learn which pydantic an interpreter has; the message says why."""


def lies_inside(path: Path, target: Path) -> bool:
    resolved = Path(os.path.realpath(path))
    return resolved == target or target in resolved.parents


def find_interpreter(command: str, target: Path) -> Optional[Path]:
    """What the system would start for command from the target: a path as it is, a bare name by the PATH, never the shim."""
    if "/" in command:
        return target / command
    shim = (REPO_ROOT / SHIM_SOURCE).read_bytes()
    for entry in os.environ.get("PATH", os.defpath).split(os.pathsep):
        candidate = target / entry / command
        if not (os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
            continue
        if candidate.stat().st_size != len(shim) or candidate.read_bytes() != shim:
            return candidate
    return None


def run_check(interpreter: Path, target: Path) -> dict:
    """What tools/check_pydantic.py prints under interpreter, run from the target with no option."""
    try:
        done = run_process.run([str(interpreter), str(REPO_ROOT / CHECK_SOURCE)], cwd=target, timeout=CHECK_TIMEOUT)
    except (OSError, ValueError) as exc:
        raise CannotTell(f"it cannot be run: {exc}") from exc
    except TIMED_OUT as exc:
        raise CannotTell(f"it did not answer within {CHECK_TIMEOUT:.0f} seconds") from exc
    if done.returncode != 0:
        detail = " ".join(done.stderr.split())
        raise CannotTell(f"it exited {done.returncode}" + (f": {detail}" if detail else ""))
    lines = done.stdout.strip().splitlines()
    try:
        answer = json.loads(lines[-1]) if lines else None
    except ValueError:
        answer = None
    if not (isinstance(answer, dict) and set(answer) == CHECK_KEYS and isinstance(answer["executable"], str)
            and isinstance(answer["prefix"], str) and (answer["pydantic"] is None or isinstance(answer["pydantic"], str))):
        raise CannotTell("the last line of its output is not the JSON object that tools/check_pydantic.py prints")
    return answer


def pip_command(executable: str) -> str:
    return f"{shlex.quote(executable)} -m pip install pydantic=={pydantic_pin()}"


def python_check(command: str, target: Path) -> tuple[list[str], Optional[dict]]:
    """The `python:` lines of the report, the interpreter the validator will start with and the pydantic it has, and what the
    check printed when it ran."""
    pin = pydantic_pin()
    named = command
    try:
        interpreter = find_interpreter(command, target)
        if interpreter is None:
            return [f"{PYTHON_PREFIX}no {command} was found on the PATH"], None
        named = str(interpreter)
        if lies_inside(interpreter.parent, target) or lies_inside(interpreter, target):
            return [f"{PYTHON_PREFIX}{named} lies inside {target}, so it was not run; "
                    "the environment belongs outside the repository"], None
        answer = run_check(interpreter, target)
    except (CannotTell, OSError) as exc:
        return [f"{PYTHON_PREFIX}{named}: cannot tell whether it has pydantic=={pin} ({exc})"], None
    executable, version = answer["executable"], answer["pydantic"]
    command_to_install = pip_command(executable)
    if version == pin:
        says = f"has pydantic=={pin}"
    elif version is None:
        says = f"lacks pydantic; to install the pinned version: {command_to_install}"
    else:
        says = f"has pydantic=={version} and the validator is tested with {pin}; to install the pinned version: {command_to_install}"
    lines = [f"{PYTHON_PREFIX}{executable} {says}"]
    if lies_inside(Path(answer["prefix"]), target):
        lines.append(f"{PYTHON_PREFIX}its environment, {answer['prefix']}, lies inside {target}, where the agent writes; "
                     "the environment belongs outside the repository")
    return lines, answer


def can_install_pydantic(answer: Optional[dict], target: Path) -> bool:
    """True when the check ran and printed another pydantic than the pin, or none, from an executable and a prefix outside the target."""
    return (answer is not None and answer["pydantic"] != pydantic_pin()
            and not lies_inside(Path(answer["executable"]), target) and not lies_inside(Path(answer["prefix"]), target))


def install_pydantic(answer: dict, command: str, target: Path) -> tuple[list[str], bool]:
    """Runs pip for the interpreter the check named, from the target and with the installer's environment; the lines of the report
    (with a new check when pip exited 0) and whether it did."""
    shown = pip_command(answer["executable"])
    try:
        done = run_process.run([answer["executable"], "-m", "pip", "install", f"pydantic=={pydantic_pin()}"],
                               cwd=target, timeout=PIP_TIMEOUT)
    except TIMED_OUT:
        return [f"{PIP_PREFIX}{shown} did not finish within {PIP_TIMEOUT:.0f} seconds"], False
    except (OSError, ValueError) as exc:
        return [f"{PIP_PREFIX}{shown} could not be run: {exc}"], False
    if done.returncode != 0:
        last = next((line.strip() for line in reversed(done.stderr.splitlines()) if line.strip()), "")
        return [f"{PIP_PREFIX}{shown} exited {done.returncode}" + (f": {last}" if last else "")], False
    lines, _ = python_check(command, target)
    return [f"{PIP_PREFIX}{shown} exited 0", *lines], True


def commit(target: Path, labels: list[str]) -> tuple[str, bool]:
    """Commits the files of the working tree this run wrote, and only them; the line of the report and whether it succeeded."""
    try:
        git(["add", "--", *labels], target, GIT_WRITE_TIMEOUT)
        git(["commit", "-q", "-m", COMMIT_MESSAGE, "--", *labels], target, GIT_WRITE_TIMEOUT)
        short = git(["rev-parse", "--short", "HEAD"], target)
    except Problem as exc:
        return f"{COMMIT_PREFIX}failed: {exc}", False
    return f"{COMMIT_PREFIX}{short} {COMMIT_MESSAGE}", True


def report_head(plan: Plan, target: Path, dry_run: bool, python: list[str]) -> list[str]:
    lines = [f"{PREFIX}{'dry run on' if dry_run else 'installing into'} {target}"]
    if plan.writes:
        lines += ["write:"] + [f"  {write.label}" for write in plan.writes]
    if plan.skips:
        lines += ["skip (already as the kit needs it):"] + [f"  {label}" for label in plan.skips]
    if not plan.writes:
        lines.append("nothing to do: the kit is already installed")
    return lines + python


def next_steps(plan: Plan, target: Path, committed: bool) -> list[str]:
    steps = [] if committed else ["commit the installed files; the Python shim only runs scripts committed in HEAD"]
    steps += [
        f"start Claude Code with this same PATH, so that the validator runs with the {plan.command} named above",
        f"open Claude Code in {target}; accept the folder trust and the {SERVER} server",
    ]
    return ["next steps:"] + [f"  {number}. {step}" for number, step in enumerate(steps, 1)]


def emit(lines: list[str]) -> None:
    sys.stdout.write("".join(f"{line}\n" for line in lines))


def fail(status: int, message: str) -> int:
    sys.stderr.write(PREFIX + message + "\n")
    return status


def finish(arguments: argparse.Namespace, plan: Plan, target: Path, answer: Optional[dict], head: list[str]) -> int:
    """The rest of a run after the writes: the report, then the pip and commit steps, each by its flag or its answer; the exit status."""
    asking = not arguments.no_input
    emit(head)
    status = 0
    if can_install_pydantic(answer, target):
        question = f"install pydantic=={pydantic_pin()} into {answer['executable']} with {pip_command(answer['executable'])}? [y/N] "
        if arguments.install_pydantic or (asking and confirmed(question)):
            lines, installed = install_pydantic(answer, plan.command, target)
            emit(lines)
            status = 0 if installed else 1
    labels = [write.label for write in plan.writes if not write.hook]
    committed = False
    if labels and (arguments.commit or (asking and confirmed(COMMIT_QUESTION))):
        line, committed = commit(target, labels)
        emit([line])
        if not committed:
            status = 1
    emit(next_steps(plan, target, committed))
    return status


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Installs the kit into an existing git repository. In a real run it asks three questions, one line of the "
                    "standard input each: which paths to govern besides the minimum, whether to run pip for the pinned pydantic "
                    "and whether to commit what it installed. A flag answers its question in advance; --no-input and --dry-run "
                    "ask no question, and what no flag says is no.",
    )
    parser.add_argument("--dry-run", action="store_true", help="run every check and print the plan, writing nothing")
    parser.add_argument("--no-input", action="store_true", help="ask no question: what no flag says is no")
    parser.add_argument("--govern", action="append", default=[], metavar="PATH",
                        help="govern PATH besides the minimum, a file path or a directory followed by /** (repeatable; "
                             "answers the paths question)")
    parser.add_argument("--install-pydantic", action="store_true",
                        help="run the pip command the report prints when the validator's interpreter has another pydantic or "
                             "none (answers the pip question yes)")
    parser.add_argument("--commit", action="store_true",
                        help=f'commit the files this run wrote, as "{COMMIT_MESSAGE}" (answers the commit question yes)')
    parser.add_argument("target", help="the top level of the git working tree to install into")
    arguments = parser.parse_args(argv)
    asking = not (arguments.dry_run or arguments.no_input)
    try:
        target = check_target(arguments.target)
        given = check_govern(arguments.govern, target)
        held = existing_extras(target)
        if asking and not given:
            given = ask_paths(target, held)
        plan = build_plan(target, extra_paths(held, given))
        python, answer = python_check(plan.command, target)
    except Problem as exc:
        return fail(2, str(exc))
    if plan.conflicts:
        sys.stderr.write(f"{PREFIX}{len(plan.conflicts)} conflict(s); nothing was written\n")
        sys.stderr.writelines(f"  {label}: {why}\n" for label, why in plan.conflicts)
        return 1
    sys.stderr.writelines(f"{PREFIX}warning: {warning}\n" for warning in plan.warnings)
    if not arguments.dry_run:
        written = []
        for write in plan.writes:
            try:
                apply(write)
            except OSError as exc:
                return fail(1, f"write failed at {write.label}: {exc}; already written, not rolled back: {', '.join(written) or 'nothing'}")
            written.append(write.label)
    gap = unsandboxed_commands_gap()
    if gap:
        sys.stderr.write(
            f"{PREFIX}warning: {gap}. A .claude/settings.local.json in a project can turn the sandbox off; "
            "sandbox.allowUnsandboxedCommands false in your own settings holds against it. "
            "The installer does not write your settings.\n"
        )
    head = report_head(plan, target, arguments.dry_run, python)
    if not arguments.dry_run:
        return finish(arguments, plan, target, answer, head)
    if arguments.install_pydantic and can_install_pydantic(answer, target):
        head.append(f"{PIP_PREFIX}a real run would run {pip_command(answer['executable'])}")
    emit([*head, DRY_RUN_CLOSING])
    return 0


if __name__ == "__main__":
    sys.exit(main())
