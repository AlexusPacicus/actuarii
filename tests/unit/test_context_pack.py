"""Volatile section extraction (tools/audit/context_pack.py, AGENTS 6.1).

A delegation contract embeds a JSON spec; the tool serves only the sections it names, to stdout,
and appends one log line per selector (path, selector, range, hashes) without the content.
Fixtures are built on a synthetic root; only the smoke test reads the real repository, and it
logs to a temporary file.
"""

import ast
import hashlib
import io
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.audit.context_pack import main

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "audit" / "context_pack.py"
ALLOWED_IMPORTS = {"__future__", "argparse", "ast", "dataclasses", "hashlib", "json", "pathlib", "re",
                   "sys", "time"}
LOG_FIELDS = {"ts", "task", "path", "kind", "value", "start", "end", "matched_lines", "sha256",
              "file_sha256", "bytes", "status", "error"}
SECRET = "TOPSECRET-4c1e"

CLAUSES = (
    "# Rules\n"
    "\n"
    "4.1 First clause.\n"
    "Continues here.\n"
    "  - an indented bullet\n"
    "\n"
    "4.2 Second clause.\n"
    "\n"
    "## Next\n"
)

HEADINGS = (
    "# Top\n"
    "intro\n"
    "## Alpha\n"
    "alpha body\n"
    "```python\n"
    "# not a heading\n"
    "```\n"
    "### Deep\n"
    "deep body\n"
    "## Beta\n"
    "beta body\n"
    "# Other\n"
)

PY = '''"""Module docstring."""
import functools

CONST = 1

DDL = """
CREATE TABLE t (
    id INTEGER
);
"""

ANNOTATED: int = 5


@functools.cache
def decorated(x):
    def inner():
        return "inner"
    return x


async def coro():
    return "coro"


class Widget:
    size = 3

    def method(self):
        return self

    @property
    def prop(self):
        return "prop"


def last():
    return "last"
'''

SYMBOLS = {
    "CONST": ("CONST = 1", "CONST = 1"),
    "DDL": ('DDL = """', '"""'),
    "ANNOTATED": ("ANNOTATED: int = 5", "ANNOTATED: int = 5"),
    "decorated": ("@functools.cache", "    return x"),
    "coro": ("async def coro():", '    return "coro"'),
    "Widget": ("class Widget:", '        return "prop"'),
    "Widget.method": ("    def method(self):", "        return self"),
    "Widget.prop": ("    @property", '        return "prop"'),
}

PARAGRAPHS = (
    "alpha one\n"
    "alpha two\n"
    "  \n"
    "beta one\n"
    "beta has needle\n"
    "\n"
    "gamma needle\n"
    "gamma two\n"
    "\n"
    "```\n"
    "fenced one\n"
    "\n"
    "fenced two\n"
    "```\n"
)

GOOD = {"task": "t", "sources": [{"path": "a.md", "select": [{"lines": "1-1"}]}]}
BAD_SPECS = {
    "not-json": "{not json",
    "not-utf8": b"\xff{}",
    "spec-not-an-object": "[]",
    "no-task": {"sources": GOOD["sources"]},
    "blank-task": {"task": " ", "sources": GOOD["sources"]},
    "no-sources": {"task": "t"},
    "empty-sources": {"task": "t", "sources": []},
    "source-without-path": {"task": "t", "sources": [{"select": [{"lines": "1-1"}]}]},
    "empty-select": {"task": "t", "sources": [{"path": "a.md", "select": []}]},
    "unknown-key": GOOD | {"sources": [{"path": "a.md", "select": [{"bogus": "x"}]}]},
    "no-key": GOOD | {"sources": [{"path": "a.md", "select": [{}]}]},
    "two-keys": GOOD | {"sources": [{"path": "a.md", "select": [{"clause": "1.1", "lines": "1-1"}]}]},
    "selector-not-an-object": GOOD | {"sources": [{"path": "a.md", "select": ["clause"]}]},
    "non-string-value": GOOD | {"sources": [{"path": "a.md", "select": [{"lines": 3}]}]},
    "bad-clause": GOOD | {"sources": [{"path": "a.md", "select": [{"clause": "one"}]}]},
    "bad-lines": GOOD | {"sources": [{"path": "a.md", "select": [{"lines": "a-b"}]}]},
    "reversed-lines": GOOD | {"sources": [{"path": "a.md", "select": [{"lines": "3-2"}]}]},
    "bad-regex": GOOD | {"sources": [{"path": "a.md", "select": [{"match": "("}]}]},
    "multiline-value": GOOD | {"sources": [{"path": "a.md", "select": [{"paragraph": "a\nb"}]}]},
}
REFUSED = ["../outside.md", "<absolute>", "sub/../ok.md", ".git/config", ".data/x", ".env", ".env.local",
           "escape.md", "envlink.md", "gitlink.md", "datalink.md", "adir", "binary.md"]


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def spec(path, *selectors, task="t"):
    return {"task": task, "sources": [{"path": path, "select": list(selectors)}]}


def parse(out):
    parts = re.split(r"^(=== .+ ===)\n", out, flags=re.MULTILINE)
    pairs = list(zip(parts[1::2], parts[2::2]))
    *sections, (pack, _) = pairs
    return [(header, body[:-1]) for header, body in sections], pack


def served(out):
    [(_, text)] = parse(out)[0]
    return text


def entries(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def failed(result, *needles):
    code, out, err = result
    assert (code, out) == (1, "")
    for needle in needles:
        assert needle in err, (needle, err)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "root"
    path.mkdir()
    return path


@pytest.fixture
def log(tmp_path):
    return tmp_path / "logs" / "pack.log"


@pytest.fixture
def invoke(monkeypatch, capsys):
    def call(raw, *argv):
        if isinstance(raw, bytes):
            stream = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
        else:
            stream = io.StringIO(raw if isinstance(raw, str) else json.dumps(raw))
        monkeypatch.setattr(sys, "stdin", stream)
        code = main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return call


@pytest.fixture
def run(invoke, root, log):
    return lambda raw, *argv: invoke(raw, "--root", str(root), "--log", str(log), *argv)


@pytest.fixture
def hostile(root):
    outside = write(root.parent, "outside.md", SECRET + "\n")
    write(root, "ok.md", "fine\n")
    write(root, ".git/config", SECRET + "\n")
    write(root, ".data/x", SECRET + "\n")
    write(root, ".env", SECRET + "\n")
    write(root, ".env.local", SECRET + "\n")
    (root / "adir").mkdir()
    (root / "binary.md").write_bytes(b"\xff\xfe" + SECRET.encode())
    (root / "escape.md").symlink_to(outside)
    (root / "envlink.md").symlink_to(root / ".env")
    (root / "gitlink.md").symlink_to(root / ".git" / "config")
    (root / "datalink.md").symlink_to(root / ".data" / "x")
    (root / "inside.md").symlink_to(root / "ok.md")
    return root


# T1 clause


def test_clause_serves_that_clause_with_its_continuation(root, run):
    write(root, "d.md", CLAUSES)
    code, out, err = run(spec("d.md", {"clause": "4.1"}))
    text = "4.1 First clause.\nContinues here.\n  - an indented bullet\n\n"
    assert code == 0, err
    assert parse(out)[0] == [(f"=== d.md:3-6 [clause=4.1] sha256={sha(text)} ===", text)]


@pytest.mark.parametrize("stop", ["4.2 Next.", "14.1 Other.", "4.10 Tenth.", "## Heading", "---", ""],
                         ids=["clause", "two-digit-clause", "tenth-clause", "heading", "rule", "eof"])
def test_clause_stops_at_the_next_clause_heading_rule_or_end(root, run, stop):
    write(root, "d.md", "4.1 First.\nmore\n" + (stop + "\n" if stop else ""))
    code, out, err = run(spec("d.md", {"clause": "4.1"}))
    assert code == 0, err
    assert served(out) == "4.1 First.\nmore\n"


def test_clause_ignores_boundaries_inside_a_code_fence(root, run):
    write(root, "d.md", "4.1 First.\n```\n4.2 fenced\n# fenced\n---\n```\ntail\n\n4.2 Second.\n")
    code, out, err = run(spec("d.md", {"clause": "4.1"}, {"clause": "4.2"}))
    assert code == 0, err
    assert [text for _, text in parse(out)[0]] == [
        "4.1 First.\n```\n4.2 fenced\n# fenced\n---\n```\ntail\n\n",
        "4.2 Second.\n",
    ]


def test_clause_number_is_not_a_prefix_match(root, run):
    write(root, "d.md", "4.10 Tenth.\n4.1 First.\n14.1 Other.\n")
    code, out, err = run(spec("d.md", {"clause": "4.1"}))
    assert code == 0, err
    assert served(out) == "4.1 First.\n"


def test_clause_absent_or_duplicated_is_an_error(root, run):
    write(root, "none.md", "4.2 Only.\n")
    write(root, "twice.md", "4.1 A.\n\n4.1 B.\n")
    failed(run(spec("none.md", {"clause": "4.1"})), "none.md", "clause=4.1", "not found")
    failed(run(spec("twice.md", {"clause": "4.1"})), "twice.md", "2 matches")


# T2 heading


@pytest.mark.parametrize("title, start, end", [("Alpha", 3, 9), ("Top", 1, 11), ("Deep", 8, 9),
                                              ("Beta", 10, 11), ("Other", 12, 12)])
def test_heading_block_runs_to_the_next_heading_of_the_same_or_higher_level(
    root, run, title, start, end
):
    write(root, "d.md", HEADINGS)
    code, out, err = run(spec("d.md", {"heading": title}))
    text = "".join(HEADINGS.splitlines(keepends=True)[start - 1:end])
    assert code == 0, err
    assert parse(out)[0] == [(f"=== d.md:{start}-{end} [heading={title}] sha256={sha(text)} ===", text)]


def test_a_heading_inside_a_code_fence_is_not_a_heading(root, run):
    write(root, "d.md", HEADINGS)
    failed(run(spec("d.md", {"heading": "not a heading"})), "heading=not a heading", "not found")


def test_a_longer_fence_is_not_closed_by_a_shorter_one(root, run):
    write(root, "d.md", "## A\n````\n```\n## fenced\n````\n## B\n")
    code, out, err = run(spec("d.md", {"heading": "A"}))
    assert code == 0, err
    assert served(out) == "## A\n````\n```\n## fenced\n````\n"
    failed(run(spec("d.md", {"heading": "fenced"})), "not found")


def test_heading_text_is_compared_after_trimming(root, run):
    write(root, "d.md", "##   Spaced title  \nbody\n")
    code, out, err = run(spec("d.md", {"heading": "Spaced title"}))
    assert code == 0, err
    assert served(out) == "##   Spaced title  \nbody\n"


def test_duplicate_heading_is_an_error(root, run):
    write(root, "d.md", "## Same\na\n## Same\nb\n")
    failed(run(spec("d.md", {"heading": "Same"})), "d.md", "heading=Same", "2 matches")


# T3 symbol


@pytest.mark.parametrize("name", list(SYMBOLS))
def test_symbol_range_and_text(root, run, name):
    write(root, "m.py", PY)
    lines = PY.splitlines()
    first, last = SYMBOLS[name]
    start, end = lines.index(first) + 1, lines.index(last) + 1
    code, out, err = run(spec("m.py", {"symbol": name}))
    text = "\n".join(lines[start - 1:end]) + "\n"
    assert code == 0, err
    assert parse(out)[0] == [(f"=== m.py:{start}-{end} [symbol={name}] sha256={sha(text)} ===", text)]


@pytest.mark.parametrize("name", ["missing", "inner", "method", "Widget.missing", "Widget.method.inner",
                                  "decorated.inner"])
def test_symbol_that_is_absent_or_not_top_level_is_an_error(root, run, name):
    write(root, "m.py", PY)
    failed(run(spec("m.py", {"symbol": name})), "m.py", f"symbol={name}", "not found")


def test_symbol_defined_twice_or_in_invalid_python_is_an_error(root, run):
    write(root, "twice.py", "def f():\n    pass\n\n\ndef f():\n    pass\n")
    write(root, "bad.py", "def (:\n")
    failed(run(spec("twice.py", {"symbol": "f"})), "2 matches")
    failed(run(spec("bad.py", {"symbol": "f"})), "not valid Python")


# T4 paragraph, T5 match, T6 lines


@pytest.mark.parametrize("literal, start, end", [("alpha", 1, 2), ("needle", 7, 8), ("```", 10, 11)])
def test_paragraph_is_the_blank_line_delimited_block_whose_first_line_has_the_literal(
    root, run, literal, start, end
):
    write(root, "d.md", PARAGRAPHS)
    code, out, err = run(spec("d.md", {"paragraph": literal}))
    text = "".join(PARAGRAPHS.splitlines(keepends=True)[start - 1:end])
    assert code == 0, err
    assert parse(out)[0] == [(f"=== d.md:{start}-{end} [paragraph={literal}] sha256={sha(text)} ===", text)]


@pytest.mark.parametrize("literal, reason", [("beta has", "not found"), ("one", "2 matches")])
def test_paragraph_absent_or_ambiguous_is_an_error(root, run, literal, reason):
    write(root, "d.md", PARAGRAPHS)
    failed(run(spec("d.md", {"paragraph": literal})), f"paragraph={literal}", reason)


def test_match_serves_every_matching_line_with_its_number(root, run, log):
    write(root, "d.md", "alpha\nbeta 1\ngamma\nbeta 2\n")
    pattern = r"^beta \d"
    code, out, err = run(spec("d.md", {"match": pattern}))
    text = "2: beta 1\n4: beta 2\n"
    assert code == 0, err
    assert parse(out)[0] == [(f"=== d.md:2-4 [match={pattern}] sha256={sha(text)} ===", text)]
    assert entries(log)[0]["matched_lines"] == [2, 4]


def test_match_without_a_line_is_an_error(root, run):
    write(root, "d.md", "alpha\n")
    failed(run(spec("d.md", {"match": "delta"})), "match=delta", "not found")


@pytest.mark.parametrize("value, start, end", [("2-3", 2, 3), ("1-4", 1, 4), ("4-4", 4, 4)])
def test_lines_serve_an_inclusive_one_based_range(root, run, value, start, end):
    write(root, "d.md", "a\nb\nc\nd\n")
    code, out, err = run(spec("d.md", {"lines": value}))
    text = "".join(f"{line}\n" for line in "abcd"[start - 1:end])
    assert code == 0, err
    assert parse(out)[0] == [(f"=== d.md:{start}-{end} [lines={value}] sha256={sha(text)} ===", text)]


@pytest.mark.parametrize("value", ["0-2", "3-5", "5-5"])
def test_lines_outside_the_file_are_an_error(root, run, value):
    write(root, "d.md", "a\nb\nc\nd\n")
    failed(run(spec("d.md", {"lines": value})), f"lines={value}", "out of range")


def test_line_endings_are_normalised_but_the_file_hash_is_of_the_bytes(root, run, log):
    raw = b"a\r\nb\rc\n"
    (root / "d.md").write_bytes(raw)
    code, out, err = run(spec("d.md", {"lines": "1-3"}))
    assert code == 0, err
    assert served(out) == "a\nb\nc\n"
    assert entries(log)[0]["file_sha256"] == sha(raw)


def test_non_ascii_text_is_served_intact(root, run):
    write(root, "d.md", "4.1 σ² ≥ θ\n")
    code, out, err = run(spec("d.md", {"clause": "4.1"}))
    assert code == 0, err
    assert served(out) == "4.1 σ² ≥ θ\n"


def test_output_layout_and_section_order(root, run):
    write(root, "a.md", "x\ny\nz\n")
    write(root, "b.md", "p\nq\n")
    body = {"task": "layout", "sources": [{"path": "b.md", "select": [{"lines": "1-2"}]},
                                          {"path": "a.md", "select": [{"match": "z"}]}]}
    code, out, err = run(body)
    first, second = "p\nq\n", "3: z\n"
    assert code == 0, err
    assert out == (
        f"=== b.md:1-2 [lines=1-2] sha256={sha(first)} ===\n{first}\n"
        f"=== a.md:3-3 [match=z] sha256={sha(second)} ===\n{second}\n"
        f"=== pack: 2 sections, {len((first + second).encode())} bytes, task=layout ===\n"
    )


def test_a_multiline_task_stays_on_the_pack_line(root, run, log):
    write(root, "a.md", "x\n")
    task = "first\n=== forged ===\nsecond"
    code, out, err = run(spec("a.md", {"lines": "1-1"}, task=task))
    assert code == 0, err
    assert len(parse(out)[0]) == 1
    assert out.endswith("task=first === forged === second ===\n")
    assert entries(log)[0]["task"] == task


# T7 all or nothing


def test_one_failing_selector_serves_nothing(root, run, log):
    write(root, "a.md", "4.1 Good.\n")
    body = {"task": "t", "sources": [
        {"path": "a.md", "select": [{"clause": "4.1"}, {"clause": "9.9"}, {"lines": "1-9"}]},
        {"path": "missing.md", "select": [{"clause": "1.1"}]},
    ]}
    result = run(body)
    failed(result, "a.md [clause=9.9]", "a.md [lines=1-9]", "missing.md [clause=1.1]")
    assert len(result[2].splitlines()) == 3
    assert [(e["path"], e["kind"], e["value"], e["status"]) for e in entries(log)] == [
        ("a.md", "clause", "9.9", "error"),
        ("a.md", "lines", "1-9", "error"),
        ("missing.md", "clause", "1.1", "error"),
    ]


# T8 path safety


@pytest.mark.parametrize("path", REFUSED)
def test_unsafe_paths_are_refused_and_logged(hostile, run, log, path):
    target = str(hostile / "ok.md") if path == "<absolute>" else path
    result = run(spec(target, {"lines": "1-1"}))
    failed(result, target, "refused")
    logged = entries(log)
    assert [(e["path"], e["status"]) for e in logged] == [(target, "error")]
    assert logged[0]["error"].startswith("refused")
    assert SECRET not in result[2] + log.read_text(encoding="utf-8")


def test_a_symlink_inside_the_root_is_served(hostile, run):
    code, out, err = run(spec("inside.md", {"lines": "1-1"}))
    assert code == 0, err
    assert served(out) == "fine\n"


def test_a_missing_file_is_an_error(root, run):
    failed(run(spec("nope.md", {"lines": "1-1"})), "nope.md", "not found")


def test_a_symlink_loop_is_an_error_not_a_crash(root, run, log):
    (root / "loop.md").symlink_to(root / "loop.md")
    failed(run(spec("loop.md", {"lines": "1-1"})), "loop.md")
    assert [e["status"] for e in entries(log)] == ["error"]


# T9 cap


def test_output_above_the_cap_is_an_error_listing_each_section(root, run, log):
    write(root, "big.md", ("x" * 499 + "\n") * 100)
    body = spec("big.md", {"lines": "1-60"}, {"lines": "61-100"})
    failed(run(body), "above the cap", "50000", "30000", "20000")
    assert {e["status"] for e in entries(log)} == {"error"}


def test_the_default_cap_is_40000_bytes(root, run):
    write(root, "big.md", ("x" * 499 + "\n") * 100)
    assert run(spec("big.md", {"lines": "1-80"}))[0] == 0
    failed(run(spec("big.md", {"lines": "1-81"})), "above the cap")


def test_max_bytes_raises_the_cap(root, run):
    write(root, "big.md", ("x" * 499 + "\n") * 100)
    body = spec("big.md", {"lines": "1-100"})
    code, out, err = run(body, "--max-bytes", "50000")
    assert code == 0, err
    assert parse(out)[1] == "=== pack: 1 sections, 50000 bytes, task=t ==="
    failed(run(body, "--max-bytes", "49999"), "above the cap")


# T10 log


def test_log_entries_have_the_exact_fields_and_types(root, run, log):
    raw = f"4.1 Clause.\n{SECRET}\n"
    write(root, "d.md", raw)
    pattern = r"TOPSECRET-\w+"
    assert not log.parent.exists()
    before = datetime.now(UTC)
    code, _, err = run(spec("d.md", {"clause": "4.1"}, {"match": pattern}, task="why"))
    assert code == 0, err
    first, second = entries(log)
    assert set(first) == set(second) == LOG_FIELDS
    clause_text, match_text = raw, f"2: {SECRET}\n"
    assert {k: v for k, v in first.items() if k != "ts"} == {
        "task": "why", "path": "d.md", "kind": "clause", "value": "4.1", "start": 1, "end": 2,
        "matched_lines": None, "sha256": sha(clause_text), "file_sha256": sha(raw),
        "bytes": len(clause_text.encode()), "status": "served", "error": None,
    }
    assert {k: v for k, v in second.items() if k != "ts"} == {
        "task": "why", "path": "d.md", "kind": "match", "value": pattern, "start": 2, "end": 2,
        "matched_lines": [2], "sha256": sha(match_text), "file_sha256": sha(raw),
        "bytes": len(match_text.encode()), "status": "served", "error": None,
    }
    stamp = datetime.strptime(first["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before - timedelta(seconds=1) <= stamp <= datetime.now(UTC) + timedelta(seconds=1)


def test_log_lines_have_sorted_keys_and_never_hold_the_content(root, run, log):
    write(root, "d.md", f"4.1 Clause.\n{SECRET}\n")
    code, _, err = run(spec("d.md", {"clause": "4.1"}, {"match": r"TOPSECRET-\w+"}))
    text = log.read_text(encoding="utf-8")
    assert code == 0, err
    assert text.endswith("\n")
    assert all(list(json.loads(line)) == sorted(json.loads(line)) for line in text.splitlines())
    assert SECRET not in text


def test_a_second_run_appends_to_the_log(root, run, log):
    write(root, "d.md", "x\n")
    assert run(spec("d.md", {"lines": "1-1"}))[0] == 0
    first_run = log.read_text(encoding="utf-8")
    assert run(spec("d.md", {"lines": "1-1"}))[0] == 0
    assert log.read_text(encoding="utf-8").startswith(first_run)
    assert len(entries(log)) == 2


def test_error_entries_carry_the_reason_and_no_measurements(root, run, log):
    write(root, "d.md", "4.2 Only.\n")
    run(spec("d.md", {"clause": "4.1"}))
    [entry] = entries(log)
    assert set(entry) == LOG_FIELDS
    assert entry["status"] == "error"
    assert "not found" in entry["error"]
    assert [entry[k] for k in ("start", "end", "matched_lines", "sha256", "bytes")] == [None] * 5
    assert entry["file_sha256"] == sha(b"4.2 Only.\n")


# T11 volatile, T12 determinism


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() if p.is_file() else None
            for p in root.rglob("*")}


@pytest.mark.parametrize("lines", ["1-1", "9-9"], ids=["served", "failed"])
def test_only_the_log_is_written(root, invoke, monkeypatch, tmp_path, lines):
    write(root, "a.md", "x\n")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    before = snapshot(root)
    invoke(spec("a.md", {"lines": lines}), "--root", str(root))
    after = snapshot(root)
    assert after.keys() - before.keys() == {".data", ".data/context_pack.log"}
    assert all(after[k] == before[k] for k in before)
    assert list(cwd.iterdir()) == []


def test_two_runs_print_identical_bytes(root, run):
    write(root, "d.md", CLAUSES)
    write(root, "m.py", PY)
    body = {"task": "same", "sources": [
        {"path": "d.md", "select": [{"clause": "4.1"}, {"match": "clause"}]},
        {"path": "m.py", "select": [{"symbol": "Widget.method"}]},
    ]}
    first, second = run(body), run(body)
    assert first == second
    assert first[0] == 0
    assert len(parse(first[1])[0]) == 3
    assert not re.search(r"\d{4}-\d{2}-\d{2}", first[1])


# T13 exit code 2


@pytest.mark.parametrize("raw", list(BAD_SPECS.values()), ids=list(BAD_SPECS))
def test_an_invalid_spec_exits_2_with_nothing_served(root, run, log, raw):
    write(root, "a.md", "x\n")
    code, out, err = run(raw)
    assert (code, out) == (2, "")
    assert err
    assert not log.exists()


@pytest.mark.parametrize("lines", ["1-1", "9-9"], ids=["would-serve", "would-fail"])
def test_an_unwritable_log_exits_2_with_nothing_served(root, run, tmp_path, lines):
    write(root, "a.md", "x\n")
    blocker = write(tmp_path, "file", "x")
    for bad in (tmp_path, blocker / "pack.log"):
        code, out, err = run(spec("a.md", {"lines": lines}), "--log", str(bad))
        assert (code, out) == (2, "")
        assert "log" in err


@pytest.mark.parametrize("argv", [["--max-bytes", "0"], ["--max-bytes", "many"], ["--root", "missing-dir"],
                                  ["--bogus"]])
def test_usage_errors_exit_2(invoke, capsys, argv):
    with pytest.raises(SystemExit) as raised:
        invoke(GOOD, *argv)
    assert raised.value.code == 2
    assert capsys.readouterr().out == ""


# T14 smoke on the real repository


def test_the_real_repository_resolves(invoke, tmp_path):
    body = {"task": "smoke", "sources": [
        {"path": "AGENTS.md", "select": [{"clause": "6.1"}]},
        {"path": "docs/audit/AUDIT.md", "select": [{"match": "R1-INV4"}]},
        {"path": "traianus/storage/_storage.py", "select": [{"symbol": "init_relational_tables"}]},
    ]}
    code, out, err = invoke(body, "--root", str(REPO_ROOT), "--log", str(tmp_path / "pack.log"))
    assert code == 0, err
    sections, pack = parse(out)
    assert [header.split(":")[0] for header, _ in sections] == [
        "=== AGENTS.md", "=== docs/audit/AUDIT.md", "=== traianus/storage/_storage.py"]
    assert all(text.strip() for _, text in sections)
    assert pack.startswith("=== pack: 3 sections, ")


# The tool itself


def test_tool_imports_only_the_allowed_standard_library_modules():
    roots = set()
    for node in ast.walk(ast.parse(TOOL.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots, "no import found: the scan would pass on anything"
    assert roots <= ALLOWED_IMPORTS, roots - ALLOWED_IMPORTS


def test_tool_postpones_annotations_for_old_system_interpreters():
    tree = ast.parse(TOOL.read_text(encoding="utf-8"), feature_version=(3, 9))
    assert any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               and any(a.name == "annotations" for a in n.names) for n in tree.body)
