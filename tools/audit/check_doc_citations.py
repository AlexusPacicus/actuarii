"""Verify the code and test citations in a traceability document (AGENTS 5.3).

An entry starts at a heading line `### <ID> — <title>` (em dash U+2014) and carries four field
lines: `En palabras` (once), one or more `Code` citations (`` `<path>:<line>` — «`<anchor>`» ``,
the anchor normative, the line derived from it), one or more `Test` citations
(`` `<path>::<name>` `` or `` `<path>::<Class>::<name>` ``), and `Source` (once). The script reads
files as text and parses cited test files with `ast`; it never imports or executes the code it
cites.

    python3 tools/audit/check_doc_citations.py [--root DIR] [--fix] [DOC]

DOC defaults to docs/traceability/TRACEABILITY.md, resolved against --root (default: the
repository root). Every cited path is resolved against --root; a cited Code path may be anywhere
under --root, a cited Test path must be under tests/. Exit 0: every entry valid; stdout is one
line `OK <entries> entries, <code> code citations, <tests> test citations`. Exit 1: at least one
error; without --fix stdout stays empty and every error is written to stderr, one line
`<DOC>:<doc line>: <ID>: <message>` (`-` as ID outside any entry), in document order. Exit 2: DOC
missing or not strict UTF-8, or bad usage.

--fix rewrites, in place, the line number of every Code citation whose only defect is a stale
line (the anchor is unique and the path resolves, only the cited line is wrong); every other byte
of DOC, including its final newline, is unchanged. Each rewrite prints
`fixed <DOC>:<doc line>: <ID>: <cited> -> <actual>` to stdout. Remaining errors are reported as
without --fix; the exit code is 0 only if nothing remains after fixing. Without --fix, DOC is
never written.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DOC = "docs/traceability/TRACEABILITY.md"

HEADING_RE = re.compile(r"^### ([A-Z][A-Z0-9-]*) — (.+)$")
FIELD_KEY_RE = re.compile(r"^- \*\*([^*:]+):\*\*")
EN_PALABRAS_RE = re.compile(r"^- \*\*En palabras:\*\* (\S.*)$")
SOURCE_RE = re.compile(r"^- \*\*Source:\*\* (\S.*)$")
CODE_RE = re.compile(r"^- \*\*Code:\*\* `([^`:]+):([^`]+)` — «`([^`]+)`»$")
TEST_RE = re.compile(r"^- \*\*Test:\*\* `([^`]+)`$")
LINE_NUMBER_RE = re.compile(r"[1-9]\d*")


@dataclass
class Entry:
    id: str
    heading_line: int
    en_palabras: list[tuple[int, str]] = field(default_factory=list)
    code: list[tuple[int, str, int, str, re.Match]] = field(default_factory=list)
    test: list[tuple[int, str]] = field(default_factory=list)
    source: list[tuple[int, str]] = field(default_factory=list)


def parse_document(lines: list[str]) -> tuple[list[Entry], list[tuple[int, str, str]]]:
    entries: list[Entry] = []
    errors: list[tuple[int, str, str]] = []
    seen_ids: set[str] = set()
    current: Entry | None = None
    for lineno, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            if current is not None:
                entries.append(current)
            entry_id = heading.group(1)
            current = Entry(entry_id, lineno)
            if entry_id in seen_ids:
                errors.append((lineno, entry_id, f"duplicate ID '{entry_id}'"))
            seen_ids.add(entry_id)
            continue
        if not line.startswith("- **"):
            continue
        if current is None:
            errors.append((lineno, "-", "field line before the first entry heading"))
            continue
        key_match = FIELD_KEY_RE.match(line)
        key = key_match.group(1) if key_match else None
        eid = current.id
        if key == "En palabras":
            m = EN_PALABRAS_RE.match(line)
            if m:
                current.en_palabras.append((lineno, m.group(1)))
            else:
                errors.append((lineno, eid, "malformed 'En palabras' field"))
        elif key == "Code":
            m = CODE_RE.match(line)
            if m:
                path_str, line_str, anchor = m.group(1), m.group(2), m.group(3)
                if LINE_NUMBER_RE.fullmatch(line_str):
                    current.code.append((lineno, path_str, int(line_str), anchor, m))
                else:
                    errors.append((lineno, eid, f"invalid line number '{line_str}'"))
            else:
                errors.append((lineno, eid, "malformed Code field"))
        elif key == "Test":
            m = TEST_RE.match(line)
            if m:
                current.test.append((lineno, m.group(1)))
            else:
                errors.append((lineno, eid, "malformed Test field"))
        elif key == "Source":
            m = SOURCE_RE.match(line)
            if m:
                current.source.append((lineno, m.group(1)))
            else:
                errors.append((lineno, eid, "malformed 'Source' field"))
        else:
            errors.append((lineno, eid, f"unknown field '{key}'" if key else "malformed field line"))
    if current is not None:
        entries.append(current)
    return entries, errors


def structural_errors(entry: Entry) -> list[tuple[int, str, str]]:
    errors: list[tuple[int, str, str]] = []
    if not entry.en_palabras:
        errors.append((entry.heading_line, entry.id, "missing 'En palabras'"))
    elif len(entry.en_palabras) > 1:
        errors.append((entry.en_palabras[1][0], entry.id, "'En palabras' appears more than once"))
    if not entry.source:
        errors.append((entry.heading_line, entry.id, "missing 'Source'"))
    elif len(entry.source) > 1:
        errors.append((entry.source[1][0], entry.id, "'Source' appears more than once"))
    if not entry.code:
        errors.append((entry.heading_line, entry.id, "missing 'Code'"))
    if not entry.test:
        errors.append((entry.heading_line, entry.id, "missing 'Test'"))
    return errors


def _resolve_under_root(root: Path, raw: str) -> Path | str:
    given = Path(raw)
    if given.is_absolute():
        return "path must be relative"
    if ".." in given.parts:
        return "path must not contain '..'"
    try:
        resolved = (root / given).resolve()
    except (OSError, RuntimeError) as exc:
        return f"path cannot be resolved ({exc})"
    if not resolved.is_relative_to(root):
        return "path resolves outside the root"
    return resolved


def validate_code_citation(root: Path, path_str: str, cited_line: int,
                            anchor: str) -> tuple[str, str | int | None]:
    resolved = _resolve_under_root(root, path_str)
    if isinstance(resolved, str):
        return "error", resolved
    if not resolved.exists() or not resolved.is_file():
        return "error", "file not found"
    try:
        text = resolved.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return "error", "file is not valid UTF-8"
    except OSError as exc:
        return "error", f"file unreadable ({exc.strerror})"
    count = text.count(anchor)
    if count == 0:
        return "error", "anchor not found"
    if count > 1:
        return "error", f"anchor ambiguous ({count} occurrences)"
    idx = text.index(anchor)
    actual_line = text.count("\n", 0, idx) + 1
    if actual_line != cited_line:
        return "stale", actual_line
    return "ok", None


def validate_test_citation(root: Path, spec_str: str) -> tuple[str, str]:
    parts = spec_str.split("::")
    if len(parts) == 2:
        path_str, class_name, func_name = parts[0], None, parts[1]
    elif len(parts) == 3:
        path_str, class_name, func_name = parts
    else:
        return "error", "malformed test spec"
    if not path_str or not func_name or (class_name is not None and not class_name):
        return "error", "malformed test spec"
    given = Path(path_str)
    if given.is_absolute() or ".." in given.parts:
        return "error", "path must be relative and free of '..'"
    if given.parts[0] != "tests":
        return "error", "path must be under tests/"
    resolved = _resolve_under_root(root, path_str)
    if isinstance(resolved, str):
        return "error", resolved
    if not resolved.exists() or not resolved.is_file():
        return "error", "file not found"
    try:
        source = resolved.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return "error", "file is not valid UTF-8"
    try:
        tree = ast.parse(source, filename=path_str)
    except SyntaxError as exc:
        return "error", f"file is not valid Python ({exc})"
    if class_name is None:
        found = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func_name
                    for n in tree.body)
        if not found:
            return "error", f"function '{func_name}' not found at module level"
        return "ok", ""
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name]
    if not classes:
        return "error", f"class '{class_name}' not found at module level"
    found = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func_name
                for cls in classes for n in cls.body)
    if not found:
        return "error", f"method '{class_name}.{func_name}' not found"
    return "ok", ""


def _citation_errors(root: Path, entries: list[Entry]) -> tuple[list[tuple[int, str, str]],
                                                                  list[tuple[int, str, int, int, re.Match]]]:
    errors: list[tuple[int, str, str]] = []
    fixups: list[tuple[int, str, int, int, re.Match]] = []
    for entry in entries:
        for lineno, path_str, cited_line, anchor, match in entry.code:
            status, detail = validate_code_citation(root, path_str, cited_line, anchor)
            if status == "error":
                errors.append((lineno, entry.id, str(detail)))
            elif status == "stale":
                actual_line = int(detail)
                errors.append(_fixed_error(lineno, entry.id, cited_line, actual_line))
                fixups.append((lineno, entry.id, cited_line, actual_line, match))
        for lineno, spec_str in entry.test:
            status, detail = validate_test_citation(root, spec_str)
            if status == "error":
                errors.append((lineno, entry.id, detail))
    return errors, fixups


def _fixed_error(lineno: int, entry_id: str, cited: int, actual: int) -> tuple[int, str, str]:
    return lineno, entry_id, f"stale line {cited}, anchor is on line {actual}"


def apply_fixes(text: str, fixups: list[tuple[int, str, int, int, re.Match]],
                 doc_display: str) -> tuple[str, list[str]]:
    content_lines = text.splitlines()
    keepend_lines = text.splitlines(keepends=True)
    messages = []
    for lineno, entry_id, cited, actual, match in fixups:
        idx = lineno - 1
        line = content_lines[idx]
        start, end = match.start(2), match.end(2)
        new_line = line[:start] + str(actual) + line[end:]
        terminator = keepend_lines[idx][len(line):]
        content_lines[idx] = new_line
        keepend_lines[idx] = new_line + terminator
        messages.append(f"fixed {doc_display}:{lineno}: {entry_id}: {cited} -> {actual}")
    return "".join(keepend_lines), messages


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("doc", nargs="?", default=DEFAULT_DOC)
    args = parser.parse_args(argv)
    root = (args.root or REPO_ROOT).resolve()
    if not root.is_dir():
        parser.error(f"--root {args.root} is not a directory")

    doc_arg = Path(args.doc)
    doc_abs = doc_arg if doc_arg.is_absolute() else root / doc_arg
    try:
        raw = doc_abs.read_bytes()
    except OSError as exc:
        sys.stderr.write(f"{args.doc}: cannot read ({exc.strerror or exc})\n")
        return 2
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        sys.stderr.write(f"{args.doc}: not valid UTF-8 ({exc})\n")
        return 2

    lines = text.splitlines()
    entries, parse_errors = parse_document(lines)
    structural: list[tuple[int, str, str]] = []
    for entry in entries:
        structural.extend(structural_errors(entry))
    citation_errors, fixups = _citation_errors(root, entries)

    all_errors = [*parse_errors, *structural, *citation_errors]
    if not entries:
        all_errors.append((1, "-", "document has no entries"))
    all_errors.sort(key=lambda e: e[0])

    fixed_messages: list[str] = []
    if args.fix and fixups:
        new_text, fixed_messages = apply_fixes(text, fixups, args.doc)
        doc_abs.write_bytes(new_text.encode("utf-8"))
        fixed_errors = {_fixed_error(lineno, eid, cited, actual)
                         for lineno, eid, cited, actual, _match in fixups}
        all_errors = [e for e in all_errors if e not in fixed_errors]

    sys.stdout.write("".join(f"{m}\n" for m in fixed_messages))

    if all_errors:
        sys.stderr.write("".join(f"{args.doc}:{lineno}: {eid}: {msg}\n" for lineno, eid, msg in all_errors))
        return 1

    code_count = sum(len(e.code) for e in entries)
    test_count = sum(len(e.test) for e in entries)
    sys.stdout.write(f"OK {len(entries)} entries, {code_count} code citations, {test_count} test citations\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
