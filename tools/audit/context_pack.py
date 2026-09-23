"""Serve exactly the sections a delegation contract names, from memory to stdout.

The contract embeds a small JSON spec; the tool prints only those sections and appends one log
line per selector (path, selector, line range, hashes; never the content). Nothing else is
written: no temporary or cache files.

    python3 tools/audit/context_pack.py [--root DIR] [--log PATH] [--max-bytes N] <<'EOF'
    {"task": "why these sections",
     "sources": [{"path": "AGENTS.md", "select": [{"clause": "6.1"}, {"heading": "Scope"}]},
                 {"path": "traianus/storage/_storage.py",
                  "select": [{"symbol": "init_relational_tables"}]}]}
    EOF

Selectors (an object with exactly one key):
    clause     "N.M": from the line starting `N.M ` to the line before the next line starting
               `<digits>.<digits> `, a heading (`#`) or a `---` rule.
    heading    the heading with that text; runs to the next heading of the same or higher level.
    symbol     a Python top-level def, async def, class or assignment (decorators included);
               `Class.method` for members. Nested functions are not selectable.
    paragraph  the block whose first line contains the literal.
    match      every line matching the regex, printed as `<lineno>: <line>`.
    lines      "a-b", 1-based inclusive, inside the file.

Lines inside ``` fences are never clause starts, clause ends or headings. Blank (whitespace
only) lines separate paragraphs everywhere, fences included. Clause, heading, symbol and
paragraph must match exactly once; match needs at least one line. Line endings are normalised
to \\n, and a blank line that ends a clause or heading block is part of it. Paths are relative
to the root; `.git`, `.data` and `.env*` are refused, as is anything resolving outside the root
or not valid UTF-8. The total served text is capped (--max-bytes, default 40000).

Exit 0: served. Exit 1: some section could not be served; nothing is printed and every failure
is listed on stderr. Exit 2: bad spec or usage, or the log cannot be appended; nothing is
printed. Every failure of exit 1 is logged; served sections are logged before they are printed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MAX_BYTES = 40000
REFUSED_PARTS = {".git", ".data"}
CLAUSE_NUMBER = re.compile(r"\d+\.\d+")
CLAUSE_START = re.compile(r"\d+\.\d+ ")
HEADING = re.compile(r"(#{1,6})[ \t]+(.*?)[ \t]*$")
LINE_RANGE = re.compile(r"(\d+)-(\d+)")


class SpecError(Exception):
    """The spec cannot be used (exit 2)."""


class SectionError(Exception):
    """A section cannot be served (exit 1)."""

    def __init__(self, reason: str, file_sha256: str | None = None):
        super().__init__(reason)
        self.file_sha256 = file_sha256


@dataclass
class Span:
    start: int
    end: int
    text: str
    matched: list[int] | None = None


@dataclass
class Section:
    path: str
    kind: str
    value: str
    file_sha256: str | None = None
    span: Span | None = None
    error: str | None = None

    @property
    def selector(self) -> str:
        return f"[{self.kind}={self.value}]"

    @property
    def size(self) -> int:
        return len(self.span.text.encode("utf-8")) if self.span else 0


@dataclass
class Spec:
    task: str
    sources: list[tuple[str, list[tuple[str, str]]]]


def _sha(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def _span(lines: list[str], first: int, stop: int) -> Span:
    return Span(first + 1, stop, "\n".join(lines[first:stop]) + "\n")


def _one(found: list):
    if not found:
        raise SectionError("not found")
    if len(found) > 1:
        raise SectionError(f"ambiguous: {len(found)} matches")
    return found[0]


def _fenced(lines: list[str]) -> list[bool]:
    """True for each line inside a ``` fence, the fence lines themselves included."""
    mask, fence = [], 0
    for line in lines:
        stripped = line.strip()
        ticks = len(stripped) - len(stripped.lstrip("`"))
        if fence:
            mask.append(True)
            if ticks >= fence and ticks == len(stripped):
                fence = 0
        else:
            mask.append(ticks >= 3)
            if ticks >= 3:
                fence = ticks
    return mask


def _ends_clause(line: str) -> bool:
    return bool(CLAUSE_START.match(line) or HEADING.match(line) or line.rstrip() == "---")


def _clause(lines: list[str], value: str) -> Span:
    fenced = _fenced(lines)
    first = _one([i for i, line in enumerate(lines) if not fenced[i] and line.startswith(f"{value} ")])
    stop = next((i for i in range(first + 1, len(lines)) if not fenced[i] and _ends_clause(lines[i])),
                len(lines))
    return _span(lines, first, stop)


def _heading(lines: list[str], value: str) -> Span:
    fenced = _fenced(lines)
    found = [(i, len(m[1]), m[2]) for i, line in enumerate(lines)
             if not fenced[i] and (m := HEADING.match(line))]
    first, level, _ = _one([h for h in found if h[2] == value])
    stop = next((i for i, other, _ in found if i > first and other <= level), len(lines))
    return _span(lines, first, stop)


def _defines(node: ast.AST, name: str) -> bool:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name == name
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name


def _symbol(lines: list[str], value: str) -> Span:
    try:
        body = ast.parse("\n".join(lines)).body
    except (SyntaxError, ValueError) as exc:
        raise SectionError(f"not valid Python: {exc}") from exc
    *owners, name = value.split(".")
    for owner in owners:
        body = _one([n for n in body if isinstance(n, ast.ClassDef) and n.name == owner]).body
    node = _one([n for n in body if _defines(n, name)])
    first = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
    return _span(lines, first - 1, node.end_lineno)


def _paragraph(lines: list[str], value: str) -> Span:
    blocks, first = [], None
    for i, line in enumerate([*lines, ""]):
        if line.strip():
            first = i if first is None else first
        elif first is not None:
            blocks.append((first, i))
            first = None
    return _span(lines, *_one([b for b in blocks if value in lines[b[0]]]))


def _match(lines: list[str], value: str) -> Span:
    hits = [i for i, line in enumerate(lines) if re.search(value, line)]
    if not hits:
        raise SectionError("not found")
    return Span(hits[0] + 1, hits[-1] + 1, "".join(f"{i + 1}: {lines[i]}\n" for i in hits),
                [i + 1 for i in hits])


def _range(lines: list[str], value: str) -> Span:
    start, end = map(int, value.split("-"))
    if not 1 <= start <= end <= len(lines):
        raise SectionError(f"out of range: the file has {len(lines)} lines")
    return _span(lines, start - 1, end)


SELECTORS = {"clause": _clause, "heading": _heading, "symbol": _symbol,
             "paragraph": _paragraph, "match": _match, "lines": _range}


def _string(value: object, what: str, *, multiline: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{what} must be a non-empty string")
    if not multiline and ("\n" in value or "\r" in value):
        raise SpecError(f"{what} must be a single line")
    return value


def _selector(path: str, selector: object) -> tuple[str, str]:
    if not isinstance(selector, dict) or len(selector) != 1:
        raise SpecError(f"{path}: a selector is an object with exactly one key, got {selector!r}")
    [(kind, raw)] = selector.items()
    if kind not in SELECTORS:
        raise SpecError(f"{path}: unknown selector key {kind!r}")
    value = _string(raw, f"{path}: the {kind} value")
    if kind == "clause" and not CLAUSE_NUMBER.fullmatch(value):
        raise SpecError(f"{path}: a clause is 'N.M', got {value!r}")
    if kind == "lines":
        bounds = LINE_RANGE.fullmatch(value)
        if not bounds or int(bounds[1]) > int(bounds[2]):
            raise SpecError(f"{path}: lines is 'a-b' with a <= b, got {value!r}")
    if kind == "match":
        try:
            re.compile(value)
        except re.error as exc:
            raise SpecError(f"{path}: the match regex is invalid: {exc}") from exc
    return kind, value


def parse_spec(raw: str) -> Spec:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SpecError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("the spec must be a JSON object")
    task = _string(data.get("task"), "task", multiline=True)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SpecError("sources must be a non-empty list")
    parsed = []
    for source in sources:
        if not isinstance(source, dict):
            raise SpecError("each source must be an object")
        path = _string(source.get("path"), "a source path")
        select = source.get("select")
        if not isinstance(select, list) or not select:
            raise SpecError(f"{path}: select must be a non-empty list")
        parsed.append((path, [_selector(path, s) for s in select]))
    return Spec(task, parsed)


def _refused(path: Path) -> bool:
    return bool(REFUSED_PARTS & set(path.parts)) or path.name.startswith(".env")


def load(root: Path, rel: str) -> tuple[list[str], str]:
    """The file's lines (line endings normalised) and the sha256 of its bytes, or a refusal."""
    given = Path(rel)
    if given.is_absolute() or ".." in given.parts:
        raise SectionError("refused: the path must be relative and free of '..'")
    if _refused(given):
        raise SectionError("refused: .git, .data and .env files are never served")
    try:
        target = (root / given).resolve()
    except (OSError, RuntimeError) as exc:
        raise SectionError(f"refused: the path cannot be resolved ({exc})") from exc
    if not target.is_relative_to(root):
        raise SectionError("refused: the path resolves outside the root")
    if _refused(target.relative_to(root)):
        raise SectionError("refused: the path resolves to .git, .data or an env file")
    if not target.exists():
        raise SectionError("file not found")
    if not target.is_file():
        raise SectionError("refused: not a regular file")
    try:
        data = target.read_bytes()
    except OSError as exc:
        raise SectionError(f"unreadable: {exc.strerror}") from exc
    digest = _sha(data)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SectionError("refused: not valid UTF-8", digest) from exc
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return (lines[:-1] if lines[-1] == "" else lines), digest


def _sections(root: Path, path: str, selectors: list[tuple[str, str]]) -> list[Section]:
    try:
        lines, digest = load(root, path)
    except SectionError as exc:
        return [Section(path, kind, value, exc.file_sha256, error=str(exc)) for kind, value in selectors]
    sections = []
    for kind, value in selectors:
        section = Section(path, kind, value, digest)
        try:
            section.span = SELECTORS[kind](lines, value)
        except SectionError as exc:
            section.error = str(exc)
        sections.append(section)
    return sections


def _apply_cap(sections: list[Section], max_bytes: int) -> None:
    total = sum(s.size for s in sections)
    if total > max_bytes:
        for section in sections:
            section.error = (f"pack of {total} bytes is above the cap of {max_bytes}; "
                             f"this section is {section.size} bytes")


def _entry(stamp: str, task: str, section: Section) -> dict:
    span = None if section.error else section.span
    return {
        "ts": stamp, "task": task, "path": section.path, "kind": section.kind, "value": section.value,
        "start": span.start if span else None,
        "end": span.end if span else None,
        "matched_lines": span.matched if span else None,
        "sha256": _sha(span.text) if span else None,
        "file_sha256": section.file_sha256,
        "bytes": section.size if span else None,
        "status": "error" if section.error else "served",
        "error": section.error,
    }


def _append_log(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries))


def _render(sections: list[Section], task: str) -> str:
    parts = []
    for section in sections:
        span = section.span
        header = f"=== {section.path}:{span.start}-{span.end} {section.selector} sha256={_sha(span.text)} ==="
        parts.append(f"{header}\n{span.text}\n")
    total = sum(s.size for s in sections)
    parts.append(f"=== pack: {len(sections)} sections, {total} bytes, task={' '.join(task.split())} ===\n")
    return "".join(parts)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--log", type=Path, help="default: <root>/.data/context_pack.log")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"--root {args.root} is not a directory")
    if args.max_bytes < 1:
        parser.error("--max-bytes must be a positive integer")
    log = args.log or root / ".data" / "context_pack.log"
    try:
        spec = parse_spec(sys.stdin.read())
    except (SpecError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"spec error: {exc}\n")
        return 2
    sections = [s for path, selectors in spec.sources for s in _sections(root, path, selectors)]
    if all(s.error is None for s in sections):
        _apply_cap(sections, args.max_bytes)
    failures = [s for s in sections if s.error]
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        _append_log(log, [_entry(stamp, spec.task, s) for s in failures or sections])
    except OSError as exc:
        sys.stderr.write(f"log not writable: {log}: {exc}\n")
        return 2
    if failures:
        sys.stderr.write("".join(f"{s.path} {s.selector}: {s.error}\n" for s in failures))
        return 1
    sys.stdout.buffer.write(_render(sections, spec.task).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
