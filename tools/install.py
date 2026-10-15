"""Installs the kit into an existing git repository without overwriting anything.

Run by the person, outside any session, from a clone of Actuarii:

    python3 tools/install.py [--dry-run] <target>

The target must be the top level of a git working tree and not the clone itself; otherwise the exit status is 2
and nothing is written. It receives, from the clone's working tree:

* every file under tools/ (without __pycache__ and *.pyc) and under .claude/agents/ and .claude/skills/, with its
  bytes and executable bit, always as a regular file: the kit's own pre-commit hook refuses a link. A symbolic link
  of the clone is installed as the regular file it resolves to, with that file's bytes and executable bit, provided
  it resolves to a regular file inside those trees; any other link (dangling, in a loop, to a directory or to
  something outside them) is a problem of the clone: exit status 2, the path on stderr, nothing written;
* .actuarii.json, when absent, with an example configuration;
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
inside the target; it prints the pip command that would install the pin and never runs it.

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
TIMED_OUT = run_process.subprocess.TimeoutExpired
PYTHON_PREFIX = "python: "
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


def git(arguments: list[str], cwd: Path) -> str:
    try:
        done = run_process.run(["git", *arguments], cwd=cwd, timeout=30.0)
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


def deny_write_entries() -> list[str]:
    entries = {"./" + path.removesuffix("/**") for path in EXAMPLE_CONFIG["governed_paths"]}
    return sorted(entries | {CONFIG_ENTRY, AUDIT_DB_ENTRY})


def blocked(plan: Plan, target: Path, destination: Path) -> bool:
    """True, with the conflict recorded, when a directory on the way to the destination is not a real directory."""
    for ancestor in reversed(destination.parents):
        if target in ancestor.parents and os.path.lexists(ancestor) and (ancestor.is_symlink() or not ancestor.is_dir()):
            plan.conflict(ancestor.relative_to(target).as_posix(), "exists and is not a directory")
            return True
    return False


def plan_file(plan: Plan, label: str, destination: Path, content: bytes, mode: int) -> None:
    if not os.path.lexists(destination):
        plan.writes.append(Write(label, destination, content=content, mode=mode))
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


def plan_config(plan: Plan, target: Path) -> None:
    destination = target / CONFIG_NAME
    if not os.path.lexists(destination):
        plan.writes.append(Write(CONFIG_NAME, destination, content=dumps(EXAMPLE_CONFIG)))
        return
    try:
        existing = load_json(destination)
    except Problem as exc:
        plan.conflict(CONFIG_NAME, str(exc))
        return
    if existing == EXAMPLE_CONFIG:
        plan.skips.append(CONFIG_NAME)
    else:
        plan.conflict(CONFIG_NAME, "exists and differs from the example configuration; the installer does not adopt another")


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


def merge_settings(existing: object, permissions: dict, hooks: dict) -> tuple[object, list[str]]:
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
    deny_write.extend([entry for entry in deny_write_entries() if entry not in deny_write])
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
        plan_file(plan, shown, destination, (REPO_ROOT / GIT_HOOKS_SOURCE / name).read_bytes(), 0o755)


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


def build_plan(target: Path) -> Plan:
    permissions, hooks, server = clone_kit_settings()
    plan = Plan(server["command"])

    def merge_kit_settings(existing: object) -> tuple[object, list[str]]:
        merged, problems = merge_settings(existing, permissions, hooks)
        if not problems:
            plan.warnings.extend(bare_bash_warnings(merged))
        return merged, problems

    plan_kit(plan, target)
    plan_config(plan, target)
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


def python_lines(command: str, target: Path) -> list[str]:
    """The `python:` lines of the report: the interpreter the validator will start with and the pydantic it has."""
    pin = pydantic_pin()
    named = command
    try:
        interpreter = find_interpreter(command, target)
        if interpreter is None:
            return [f"{PYTHON_PREFIX}no {command} was found on the PATH"]
        named = str(interpreter)
        if lies_inside(interpreter.parent, target) or lies_inside(interpreter, target):
            return [f"{PYTHON_PREFIX}{named} lies inside {target}, so it was not run; "
                    "the environment belongs outside the repository"]
        answer = run_check(interpreter, target)
    except (CannotTell, OSError) as exc:
        return [f"{PYTHON_PREFIX}{named}: cannot tell whether it has pydantic=={pin} ({exc})"]
    executable, version = answer["executable"], answer["pydantic"]
    pip_command = f"{shlex.quote(executable)} -m pip install pydantic=={pin}"
    if version == pin:
        says = f"has pydantic=={pin}"
    elif version is None:
        says = f"lacks pydantic; to install the pinned version: {pip_command}"
    else:
        says = f"has pydantic=={version} and the validator is tested with {pin}; to install the pinned version: {pip_command}"
    lines = [f"{PYTHON_PREFIX}{executable} {says}"]
    if lies_inside(Path(answer["prefix"]), target):
        lines.append(f"{PYTHON_PREFIX}its environment, {answer['prefix']}, lies inside {target}, where the agent writes; "
                     "the environment belongs outside the repository")
    return lines


def report(plan: Plan, target: Path, dry_run: bool) -> str:
    lines = [f"{PREFIX}{'dry run on' if dry_run else 'installing into'} {target}"]
    if plan.writes:
        lines += ["write:"] + [f"  {write.label}" for write in plan.writes]
    if plan.skips:
        lines += ["skip (already as the kit needs it):"] + [f"  {label}" for label in plan.skips]
    if not plan.writes:
        lines.append("nothing to do: the kit is already installed")
    lines += python_lines(plan.command, target)
    next_steps = [
        "next steps:",
        "  1. commit the installed files; the Python shim only runs scripts committed in HEAD",
        f"  2. start Claude Code with this same PATH, so that the validator runs with the {plan.command} named above",
        f"  3. open Claude Code in {target}; accept the folder trust and the {SERVER} server",
    ]
    lines += [DRY_RUN_CLOSING] if dry_run else next_steps
    return "\n".join(lines) + "\n"


def fail(status: int, message: str) -> int:
    sys.stderr.write(PREFIX + message + "\n")
    return status


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="install.py", description="Installs the kit into an existing git repository.")
    parser.add_argument("--dry-run", action="store_true", help="run every check and print the plan, writing nothing")
    parser.add_argument("target", help="the top level of the git working tree to install into")
    arguments = parser.parse_args(argv)
    try:
        target = check_target(arguments.target)
        plan = build_plan(target)
        text = report(plan, target, arguments.dry_run)
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
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
