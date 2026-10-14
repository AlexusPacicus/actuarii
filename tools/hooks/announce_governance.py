"""SessionStart hook: tells the agent what the kit governs in this session and where the rule comes from.

Claude Code adds the stdout of a SessionStart hook to the agent's context, so the kit never governs in silence:
the source of the rules (.actuarii.json, the built-in minimum, or an invalid configuration), the paths whose
Edit/Write needs a receipt and for how long, the contract registry, the blind review and where Python may run. Every fact comes
from tools/project_config, never from a list kept here, so the announcement cannot diverge from the gates. It also
says whether the Bash sandbox is on (.claude/settings.json) and whether the commit-integrity hook
(tools/git/pre-commit) is installed where git would run it.

It never blocks and never fails: it always exits 0 and writes nothing to stderr, because a SessionStart hook
cannot deny anything (the PreToolUse gates do). If the project configuration cannot be imported it says so on
stdout. Standard library plus tools.project_config, and tools.audit.run_process to ask git, importable by a Python
3.9 interpreter.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

GATE_TOOL = "mcp__boundary-validator__validate_proposal"
WHOLE_REPOSITORY = ". (the whole repository)"
SETTINGS = ".claude/settings.json"
HOOK_SOURCE = "tools/git/pre-commit"
HOOK_PATH = "hooks/pre-commit"

try:
    if str(REPO_ROOT) in sys.path:
        import tools
    else:
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import tools
        finally:
            sys.path.remove(str(REPO_ROOT))
    import tools.project_config as project_config
    from tools.project_config import CONFIG_NAME, DEFAULT_WINDOW, ROOT, ConfigError, ProjectConfig, ReviewConfig, load
except Exception as exc:
    project_config = None
    IMPORT_FAILURE = f"{type(exc).__name__}: {exc}"


def _kit_dir() -> str:
    return Path(project_config.__file__).resolve().parent.relative_to(ROOT).as_posix() + "/"


def _invalid(error: Exception) -> list[str]:
    return [
        f"actuarii: {CONFIG_NAME} is invalid ({error})",
        f"  While it is invalid, every Edit/Write inside the repository is denied, except {CONFIG_NAME}, which "
        f"needs a receipt from {GATE_TOOL}, valid for {DEFAULT_WINDOW} s.",
        f"  Python runs only committed scripts, and only from {_kit_dir()} (the kit).",
        f"  First repair {CONFIG_NAME}.",
    ]


def _review(review: ReviewConfig | None) -> str:
    return "none" if review is None else f"procedure {review.procedure}, records in {review.records}"


def _sandbox_line() -> str:
    try:
        settings = json.loads((REPO_ROOT / SETTINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        settings = None
    sandbox = settings.get("sandbox") if isinstance(settings, dict) else None
    if isinstance(sandbox, dict) and sandbox.get("enabled") is True:
        return f"  Bash sandbox: on ({SETTINGS}); Bash cannot write the governed paths"
    return "  Bash sandbox: off; writes made through Bash do not pass these gates"


def _hook_line() -> str:
    try:
        from tools.audit import run_process

        source = (REPO_ROOT / HOOK_SOURCE).read_bytes()
        done = run_process.run(["git", "rev-parse", "--git-path", HOOK_PATH], cwd=REPO_ROOT, timeout=5.0)
        if done.returncode != 0 or not done.stdout.strip():
            raise OSError(f"git rev-parse --git-path exited {done.returncode}: {done.stderr.strip()}")
    except Exception as exc:
        return f"  Commit integrity hook: cannot tell ({type(exc).__name__}: {exc})"
    shown = done.stdout.strip()
    try:
        installed = (REPO_ROOT / shown).read_bytes() == source and os.access(REPO_ROOT / shown, os.X_OK)
    except OSError:
        installed = False
    if installed:
        return f"  Commit integrity hook: installed ({shown})"
    return f"  Commit integrity hook: not installed; copy {HOOK_SOURCE} to {shown} and make it executable"


def _valid(config: ProjectConfig) -> list[str]:
    registry = config.contract_registry
    receipts = dict.fromkeys([CONFIG_NAME, *([registry] if registry else []), *config.governed_paths])
    dirs = ", ".join(WHOLE_REPOSITORY if entry == "." else entry for entry in config.python_script_dirs)
    return [
        f"actuarii: the governance rules come from {config.source}",
        f"  Edit/Write needs a receipt from {GATE_TOOL}, valid for {config.receipt_window_seconds} s, on:",
        *(f"    {path}" for path in receipts),
        f"  Contract registry: {registry or 'none'}",
        f"  Blind review: {_review(config.review)}",
        f"  Python runs only committed scripts, from {_kit_dir()} (the kit) and python_script_dirs: {dirs or 'none'}",
        _sandbox_line(),
        _hook_line(),
        "  Declared limit: with the Bash sandbox on, Bash cannot write the governed paths; with it off, writes made "
        "through Bash do not pass these gates.",
    ]


def announcement() -> str:
    if project_config is None:
        return (
            f"actuarii: the project configuration could not be imported ({IMPORT_FAILURE}); "
            "the write gate denies every Edit/Write inside the repository until it is repaired.\n"
        )
    try:
        lines = _valid(load())
    except ConfigError as exc:
        lines = _invalid(exc)
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.write(announcement())
    return 0


if __name__ == "__main__":
    sys.exit(main())
