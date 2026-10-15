#!/usr/bin/env python3
"""Claude Code PreToolUse hook: no direct host authority over governed paths, whatever tool writes them.

Reads the PreToolUse JSON payload from stdin ({"tool_name": ..., "tool_input": {...}, "cwd": ...}). Exits 0
(allow) unless the payload names a governed path with no recent boundary-validator receipt, in which case
it exits 2 (blocking) with an explanatory message on stderr. Any failure to verify (bad DB, bad payload shape,
a path the filesystem cannot be asked about) fails closed.

The gate does not keep a list of the tools that write; it knows three classes of tool and denies by default:

1. Known writers, each with its path field: Edit, MultiEdit and Write (`file_path`) and NotebookEdit
   (`notebook_path`). A governed path in that field needs a receipt for the exact change, which is what the
   tool writes, hashed as the validator hashed the proposal (SHA-256 of the UTF-8 bytes, nothing normalised):
   Edit needs a receipt whose Topological_Grounding is its `old_string` and whose Implementation_Block is its
   `new_string`; MultiEdit needs one such receipt for each of its `edits`; Write needs one whose
   Implementation_Block is its `content`, with any citation; NotebookEdit needs one whose Implementation_Block
   is its `new_source` (the empty string when it has none, as when it deletes a cell), with any citation. A
   content field that is not a string, or a MultiEdit without a usable list of edits, is denied. A writer
   without its path field, or with one that is not a non-empty string, is denied: the gate cannot tell what it
   writes. A receipt is not consumed: it stays valid for the whole window.
2. Known tools that write no file, which always pass: Read, Grep, Glob, LS, NotebookRead, Bash (what it writes is
   a declared limit), BashOutput, KillShell, WebFetch, WebSearch, TodoWrite, Task, Agent, Skill, ToolSearch,
   AskUserQuestion, EnterPlanMode, ExitPlanMode, SendMessage and the boundary validator's own
   mcp__boundary-validator__validate_proposal, which receives a governed path as its target_file and must never
   be blocked.
3. Any other tool, a future one or an MCP one: every string in its tool_input, at any depth of dictionaries and
   lists, is a candidate when it is non-empty, at most 4096 characters, free of NUL and of line breaks, and
   either absolute, or starting with `~`, or containing `/`. A candidate is resolved (a relative one against the
   payload's absolute `cwd`, else against the repository root) and, when it is inside the repository and
   governed, needs a receipt for that file, with any content. The gate does not know whether such a tool
   writes, nor what, so it asks for the receipt per file.

For Edit, MultiEdit and Write on a governed `.py` path, once the receipts pass, the hook computes the exact result
from the file as it is (an Edit with `replace_all`, the edits of a MultiEdit in order, or the content of a Write),
parses it with `ast` under its own Python and denies it when it does not parse or introduces a primitive the
file does not already have (tools/boundary_validator/primitives.py). An Edit that cannot apply, because its
`old_string` is not in the file, writes nothing and gets no primitive check.

The one thing the gate writes is the record of what an allowed write leaves. Once the receipts and the primitive
check pass, and before it allows an Edit, MultiEdit or Write, it adds a row to the audit trail
(tools/boundary_validator/hook_gate.py: record_write) with the path relative to the repository, the tool, the
SHA-256 of the bytes the file has now (NULL when it does not exist), the SHA-256 of the exact result and the
case_ids of the receipts that cover the write: for each receipt the tool needs, in that order, the most recent one
that matches. The file is read once, for the primitive check and for the record; an OSError other than its absence
denies the write. The result is the content of a Write; for an Edit or a MultiEdit it is computed from the file
read as strict UTF-8, and nothing is recorded (the write is allowed, as it was) when the file is not UTF-8 or the
change cannot apply. When the row cannot be written the write is denied: a gate that cannot record what it allows
does not allow it. NotebookEdit, the tools of class 3 and a denied write record nothing. The receipt queries stay
read-only.

The governed paths and the receipt window come from the project configuration (.actuarii.json,
tools/project_config.py), and every denial names the rule behind it. While that configuration is invalid every
path inside the repository that a writer or a class 3 tool names is denied, with the error in the message,
except for the configuration file itself, which stays subject to a receipt; outside the repository nothing is
denied.

The target is decided by what the filesystem says it is, not by how it is spelled: `canonical` resolves it
(symlinks, `..`) and re-spells it with the names its directory entries store, found by identity, before the gate
looks at it. On a case-insensitive filesystem `TESTS/x.py` is therefore `tests/x.py`. A path inside the
repository that the filesystem cannot be asked about is denied, with one exception: when resolving a
candidate fails because a name is too long (ENAMETOOLONG) and the filesystem refuses one of its names looked
up alone under the repository root, no file can bear that name, so the candidate is not a path. When the
filesystem admits every name alone, it is the whole path that is too long, and the candidate is denied. A
receipt is matched against that stored spelling, so validate_proposal must be given it (the denial prints it).

Declared limits: a path hidden inside a longer string (a `file://` URL, a command line with spaces) is not
recognised as a candidate; the class 2 tools are taken as the tools that write no file; Bash does not pass
through this gate; the contract-context hook does not cover class 3 tools. The content a receipt binds is
what the tool input carries: `replace_all` of Edit is not bound (it only decides how many times the approved
change applies); the citation of NotebookEdit is not bound (its input carries only a `cell_id`, not the text
it replaces); a class 3 tool keeps the receipt per file, with any content.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import sqlite3
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    if str(REPO_ROOT) in sys.path:
        import tools
    else:
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import tools
        finally:
            sys.path.remove(str(REPO_ROOT))
    from tools.boundary_validator.hook_gate import (
        _db_path,
        audit_trail_exists,
        governing_rule,
        has_any_receipt,
        has_recent_execute_safe,
        receipt_case,
        record_write,
    )
    from tools.boundary_validator.primitives import NotPython, introduced
    from tools.project_config import CONFIG_NAME, ConfigError
except Exception as exc:  # fail-closed: a gate that cannot start must deny
    # An unhandled failure here exits 1, which the harness reads as a broken
    # hook and not as a denial: the edit would proceed ungated.
    sys.stderr.write(
        "[require_boundary_validation] fail-closed: the boundary gate could "
        f"not be imported ({exc}). Denying instead of leaving the edit "
        "ungated.\n"
    )
    sys.exit(2)

WRITERS = {
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
}
NON_WRITERS = frozenset({
    "Read", "Grep", "Glob", "LS", "NotebookRead", "Bash", "BashOutput", "KillShell", "WebFetch", "WebSearch",
    "TodoWrite", "Task", "Agent", "Skill", "ToolSearch", "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
    "SendMessage", "mcp__boundary-validator__validate_proposal",
})
MAX_CANDIDATE_LENGTH = 4096


def _same(samefile: Callable[..., bool], first: str | Path, second: Path) -> bool:
    try:
        return samefile(first, second)
    except FileNotFoundError:
        return False


def canonical(
    target: str | Path,
    root: Path,
    samefile: Callable[..., bool] = os.path.samefile,
    scandir: Callable[..., Any] = os.scandir,
) -> Path | None:
    """`target` resolved, then re-spelled with the names the filesystem stores; None outside `root`.

    A case-insensitive filesystem lets `TESTS/x.py` name `tests/x.py`, so names are matched by
    identity, never by spelling: the ancestor that is the same file as `root` is found with
    `samefile`, and below it each name becomes the directory entry that is the same file as the
    spelled one. What does not exist yet (a new file) stays as spelled. An OSError while looking for
    the root only means "not that ancestor"; past the root it propagates, and so does one on the
    root itself, so an unreadable root cannot make every path read as outside. Both hooks under
    tools/hooks carry this function; a test compares the copies.
    """
    samefile(root, root)
    path = Path(target).resolve()
    for anchor in (path, *path.parents):
        try:
            if samefile(anchor, root):
                break
        except OSError:
            continue
    else:
        return None
    real, spelled = Path(root), anchor
    names = path.relative_to(anchor).parts
    for index, name in enumerate(names):
        spelled = spelled / name
        with scandir(real) as entries:
            found = sorted(
                entry.name for entry in entries
                if not entry.is_symlink() and _same(samefile, entry.path, spelled)
            )
        if not found:
            return real.joinpath(*names[index:])
        real = real / (name if name in found else found[0])
    return real


def _refuses_a_name_alone(spelled: Path, root: Path) -> bool:
    """True when the filesystem, asked about one name of `spelled` resolved, says it is too long.

    Each name is looked up alone under `root`, so the system receives that name and nothing else: a
    refusal then means no file can bear the name, now or later. The gate counts neither bytes nor
    characters, since the limit depends on the filesystem. Any other answer, or a failure of the
    check itself, is False: the caller then denies, as it does for every other error.
    """
    try:
        resolved = spelled.resolve()
        descriptor = os.open(root, os.O_RDONLY)
        try:
            for name in resolved.relative_to(resolved.anchor).parts:
                try:
                    os.lstat(name, dir_fd=descriptor)
                except OSError as exc:
                    if exc.errno == errno.ENAMETOOLONG:
                        return True
            return False
        finally:
            os.close(descriptor)
    except (OSError, RuntimeError, ValueError):
        return False


def _is_candidate(text: str) -> bool:
    return (
        0 < len(text) <= MAX_CANDIDATE_LENGTH
        and "\0" not in text
        and "\n" not in text
        and (os.path.isabs(text) or text.startswith("~") or "/" in text)
    )


def _candidates(tool_input: Any) -> Iterator[tuple[str, str]]:
    """Every path-like string of `tool_input` with where it sits (`tool_input.args[0].path`).

    Iterative, so the depth of the input cannot exhaust the interpreter's stack.
    """
    pending = [("tool_input", tool_input)]
    while pending:
        location, item = pending.pop()
        if isinstance(item, str):
            if _is_candidate(item):
                yield location, item
        elif isinstance(item, dict):
            pending.extend((f"{location}.{key}", value) for key, value in reversed(list(item.items())))
        elif isinstance(item, list):
            pending.extend((f"{location}[{index}]", value) for index, value in reversed(list(enumerate(item))))


class ContentError(ValueError):
    """A content field of a writer that the gate cannot read as text; the message names the field."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text(holder: dict[str, Any], key: str, location: str) -> str:
    value = holder.get(key)
    if not isinstance(value, str):
        raise ContentError(f"{location}.{key} must be a string")
    return value


def _edit_receipt(edit: Any, location: str) -> tuple[str | None, str]:
    if not isinstance(edit, dict):
        raise ContentError(f"{location} must be an object with a string old_string and a string new_string")
    return _sha256(_text(edit, "old_string", location)), _sha256(_text(edit, "new_string", location))


def required_receipts(tool: str, tool_input: dict[str, Any]) -> list[tuple[str | None, str]]:
    """The receipts `tool` needs, as (grounding_sha256, block_sha256); a grounding of None is any citation.

    Raises ContentError naming the field when what the tool writes cannot be read as text.
    """
    if tool == "Edit":
        return [_edit_receipt(tool_input, "tool_input")]
    if tool == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list) or not edits:
            raise ContentError("tool_input.edits must be a non-empty list of edits")
        return [_edit_receipt(edit, f"tool_input.edits[{index}]") for index, edit in enumerate(edits)]
    if tool == "Write":
        return [(None, _sha256(_text(tool_input, "content", "tool_input")))]
    source = _text(tool_input, "new_source", "tool_input") if "new_source" in tool_input else ""
    return [(None, _sha256(source))]


def _apply_edit(current: str | None, edit: dict[str, Any]) -> str | None:
    """The file after one Edit-style change; None when the tool cannot apply it and so writes nothing."""
    old, new = edit["old_string"], edit["new_string"]
    if old == "":
        return new
    if current is None or old not in current:
        return None
    return current.replace(old, new) if edit.get("replace_all") is True else current.replace(old, new, 1)


def written_result(tool: str, tool_input: dict[str, Any], current: str | None) -> str | None:
    """The exact content of the file after Edit, MultiEdit or Write writes it over `current` (None: no file).

    None when the tool writes nothing: an Edit, or an edit of a MultiEdit, that cannot apply. Call it only once
    required_receipts has read the tool input, which makes the fields it reads strings.
    """
    if tool == "Write":
        return tool_input["content"]
    result = current
    for edit in [tool_input] if tool == "Edit" else tool_input["edits"]:
        result = _apply_edit(result, edit)
        if result is None:
            return None
    return result


def read_current(target: Path) -> bytes | None:
    """The bytes of `target`, or None when the file does not exist; any other OSError propagates."""
    try:
        return target.read_bytes()
    except FileNotFoundError:
        return None


def record(target: Path, tool: str, tool_input: dict[str, Any], data: bytes | None, cases: list[str]) -> None:
    """Records in the audit trail what `tool` leaves in `target`, which holds `data` (None: no file).

    Only Edit, MultiEdit and Write. The result is the content of a Write; for an Edit or a MultiEdit it is
    written_result over `data` as strict UTF-8, and nothing is recorded when `data` is not UTF-8 or the tool cannot
    apply. Call it only once required_receipts has read the tool input; `cases` are the case_ids of the receipts,
    in the order required_receipts gives them. An error of record_write propagates.
    """
    if tool not in ("Edit", "MultiEdit", "Write"):
        return
    if tool == "Write":
        result = tool_input["content"]
    else:
        try:
            current = None if data is None else data.decode("utf-8")
        except UnicodeDecodeError:
            return
        result = written_result(tool, tool_input, current)
        if result is None:
            return
    record_write(
        target.relative_to(REPO_ROOT).as_posix(),
        tool,
        None if data is None else hashlib.sha256(data).hexdigest(),
        _sha256(result),
        cases,
    )


def _one_line(exc: Exception) -> str:
    return f"{type(exc).__name__}: {' '.join(str(exc).split())}"


def write_denial(target: Path, tool: str, tool_input: dict[str, Any], cases: list[str]) -> str | None:
    """Why the gate denies a write whose receipts all exist, or None when it records the write and allows it."""
    try:
        data = read_current(target)
    except OSError as exc:
        return f"the gate cannot read it ({_one_line(exc)}), so it cannot tell what {tool} would leave and denies it."
    denial = primitive_denial(target, tool, tool_input, data)
    if denial is not None:
        return denial
    try:
        record(target, tool, tool_input, data, cases)
    except (sqlite3.Error, OSError) as exc:
        return (f"the gate could not record in the audit trail what {tool} leaves ({_one_line(exc)}), "
                "so it denies the write.")
    return None


def primitive_denial(target: Path, tool: str, tool_input: dict[str, Any], data: bytes | None) -> str | None:
    """Why the result of `tool` on the Python file `target`, which holds `data` (None: no file), is denied, or None.

    Only Edit, MultiEdit and Write on a `.py` path. The result is parsed with this hook's Python; it is denied when
    it does not parse or introduces a primitive the file as it is now does not have. A file that is not valid
    UTF-8 cannot be read, so it is denied too.
    """
    if tool not in ("Edit", "MultiEdit", "Write") or not target.name.lower().endswith(".py"):
        return None
    try:
        current = None if data is None else data.decode("utf-8")
    except UnicodeDecodeError:
        return f"its current content is not valid UTF-8, so the gate cannot compute what {tool} would leave."
    result = written_result(tool, tool_input, current)
    if result is None:
        return None
    try:
        new = introduced(current, result)
    except NotPython:
        return (f"the result of {tool} does not parse as Python {sys.version_info.major}.{sys.version_info.minor}, "
                "the one that runs this hook, and the gate denies what it cannot check.")
    if new:
        return (f"{tool} would introduce a network, process or code-loading primitive the file does not have: "
                f"{', '.join(new)}. A receipt does not cover it.")
    return None


OTHER_CONTENT = (
    "There are recent receipts for this file, but for other content: a receipt covers one exact change. "
    "The proposal must carry the old_string of an Edit, or of each edit of a MultiEdit, as its "
    "Topological_Grounding and the new_string as its Implementation_Block; for a Write the content, and "
    "for a NotebookEdit the new_source, is the Implementation_Block, always byte for byte. "
)


def main(
    samefile: Callable[..., bool] = os.path.samefile, scandir: Callable[..., Any] = os.scandir
) -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, RecursionError):
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: stdin was not valid "
            "JSON; cannot verify whether the target is a governed path.\n"
        )
        return 2  # R2/INV-2: unparseable input blocks, same as every other unverifiable case
    if not isinstance(payload, dict):
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: stdin was not a JSON "
            "object; cannot verify whether the target is a governed path.\n"
        )
        return 2

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    known = isinstance(tool, str)
    if known and tool in NON_WRITERS:
        return 0
    writer = known and tool in WRITERS
    if writer:
        field = WRITERS[tool]
        value = tool_input.get(field) if isinstance(tool_input, dict) else None
        if not isinstance(value, str) or not value:
            sys.stderr.write(
                f"[require_boundary_validation] fail-closed: {tool} names no usable tool_input.{field} "
                "(it must be a non-empty string); cannot tell what it writes.\n"
            )
            return 2
        candidates: Iterator[tuple[str, str]] = iter([(f"tool_input.{field}", value)])
    else:
        candidates = _candidates(tool_input)
    cwd = payload.get("cwd")
    base = Path(cwd) if isinstance(cwd, str) and os.path.isabs(cwd) else REPO_ROOT

    try:
        for location, raw in candidates:
            try:
                spelled = Path(raw).expanduser()
                if not writer and not spelled.is_absolute():
                    spelled = base / spelled
                target = canonical(spelled, REPO_ROOT, samefile, scandir)
            except (OSError, RuntimeError, ValueError) as exc:
                if (
                    isinstance(exc, OSError)
                    and exc.errno == errno.ENAMETOOLONG
                    and _refuses_a_name_alone(spelled, REPO_ROOT)
                ):
                    continue
                sys.stderr.write(
                    "[require_boundary_validation] fail-closed: cannot tell whether "
                    f"{raw!r} ({tool}, {location}) is inside the repository ({exc}).\n"
                )
                return 2
            if target is None:
                continue
            try:
                verdict = governing_rule(str(target))
            except ConfigError as exc:
                sys.stderr.write(
                    f"[require_boundary_validation] {target} is denied: the project "
                    f"configuration is invalid, so no rule can be applied ({exc}). Fix "
                    f"{CONFIG_NAME}; it stays editable under a receipt: call "
                    "mcp__boundary-validator__validate_proposal with "
                    f"target_file={REPO_ROOT / CONFIG_NAME}, then retry.\n"
                )
                return 2
            if verdict is None:
                continue
            if writer:
                try:
                    needed = required_receipts(tool, tool_input)
                except ContentError as exc:
                    sys.stderr.write(
                        f"[require_boundary_validation] fail-closed: {target} is governed by {verdict.rule} "
                        f"(source: {verdict.source}) and {tool} names no usable content: {exc}; "
                        "the gate cannot tell which receipt covers what it writes.\n"
                    )
                    return 2
            if not audit_trail_exists():
                sys.stderr.write(
                    f"[require_boundary_validation] {target} is governed by {verdict.rule} "
                    f"(source: {verdict.source}) and has no recent EXECUTE_SAFE receipt: there is no "
                    f"audit trail yet ({_db_path()} does not exist; the validator creates it on its "
                    "first call). Call mcp__boundary-validator__validate_proposal with "
                    f"target_file={target}, then retry.\n"
                )
                return 2
            if writer:
                cases = [
                    receipt_case(str(target), block, grounding, verdict.window_seconds)
                    for grounding, block in needed
                ]
                if None not in cases:
                    denial = write_denial(target, tool, tool_input, cases)
                    if denial is None:
                        continue
                    sys.stderr.write(
                        f"[require_boundary_validation] {target} is governed by {verdict.rule} "
                        f"(source: {verdict.source}) and {denial}\n"
                    )
                    return 2
                sys.stderr.write(
                    f"[require_boundary_validation] {target} is governed by {verdict.rule} "
                    f"(source: {verdict.source}) and has no recent EXECUTE_SAFE receipt for this exact "
                    f"change in audit_log (window: {verdict.window_seconds} s). "
                    + (OTHER_CONTENT if has_any_receipt(str(target), verdict.window_seconds) else "")
                    + "Call "
                    f"mcp__boundary-validator__validate_proposal with target_file={target}, "
                    "then retry.\n"
                )
                return 2
            if has_recent_execute_safe(str(target), verdict.window_seconds):
                continue
            sys.stderr.write(
                f"[require_boundary_validation] {target} is governed by {verdict.rule} "
                f"(source: {verdict.source}) and has no recent EXECUTE_SAFE in audit_log "
                f"(window: {verdict.window_seconds} s). "
                f"{tool} names it in {location}, and the gate does not know whether that tool "
                "writes files, nor what, so it asks for a receipt for the file. "
                "Call "
                f"mcp__boundary-validator__validate_proposal with target_file={target}, "
                "then retry.\n"
            )
            return 2
    except Exception as exc:  # fail-closed: an unverifiable audit trail blocks
        sys.stderr.write(
            "[require_boundary_validation] fail-closed: could not verify "
            f"the boundary-validator audit trail ({exc}).\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
