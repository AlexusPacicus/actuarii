"""Citations in a traceability document, verified mechanically (tools/audit/check_doc_citations.py,
AGENTS 5.3, 1.6).

Fixtures build a synthetic root with a source file and a tests/ fixture module; only the smoke
tests at the end read the real repository, verifying docs/traceability/TRACEABILITY.md itself.
"""

import ast
import re
from pathlib import Path

import pytest

from tools.audit.check_doc_citations import main

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "audit" / "check_doc_citations.py"
ALLOWED_IMPORTS = {"__future__", "argparse", "ast", "dataclasses", "pathlib", "re", "sys"}
DOC = "DOC.md"

TARGET_SRC = (
    "def alpha():\n"      # 1
    "    return 1\n"       # 2
    "\n"                    # 3
    "def beta():\n"        # 4
    "    return 1\n"       # 5
    "\n"                    # 6
    "class Gamma:\n"       # 7
    "    def method(self):\n"  # 8
    "        return 3\n"   # 9
)

TEST_TARGET_SRC = (
    '"""Fixture."""\n'
    "\n"
    "\n"
    "def test_top():\n"
    "    assert True\n"
    "\n"
    "\n"
    "class TestThing:\n"
    "    def test_method(self):\n"
    "        assert True\n"
    "\n"
    "    def helper(self):\n"
    "        def nested():\n"
    "            assert True\n"
    "        nested()\n"
    "\n"
    "\n"
    "# mentions test_ghost in a comment\n"
    'GHOST = "test_ghost"\n'
)


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def entry(entry_id, *, title=None, en_palabras=("algo en español.",),
          code=(("src.py", 4, "def beta():"),),
          test=("tests/unit/test_target.py::test_top",), source=("AGENTS 1.1",)):
    lines = [f"### {entry_id} — {title or entry_id.lower()}"]
    for value in en_palabras:
        lines.append(f"- **En palabras:** {value}")
    for path, lineno, anchor in code:
        lines.append(f"- **Code:** `{path}:{lineno}` — «`{anchor}`»")
    for spec in test:
        lines.append(f"- **Test:** `{spec}`")
    for value in source:
        lines.append(f"- **Source:** {value}")
    return "\n".join(lines) + "\n"


def failed(result, *needles):
    code, out, err = result
    assert (code, out) == (1, "")
    for needle in needles:
        assert needle in err, (needle, err)
    return err


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "root"
    path.mkdir()
    write(path, "src.py", TARGET_SRC)
    write(path, "tests/unit/test_target.py", TEST_TARGET_SRC)
    return path


@pytest.fixture
def invoke(capsys):
    def call(*argv):
        code = main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return call


@pytest.fixture
def run(invoke, root):
    return lambda doc_text, *argv: (
        write(root, DOC, doc_text),
        invoke("--root", str(root), *argv, DOC),
    )[1]


# T1 a valid document exits 0 with the exact OK line


def test_valid_document_exits_0_with_counts(run):
    doc = entry("C1", code=(("src.py", 4, "def beta():"), ("src.py", 7, "class Gamma:")),
                test=("tests/unit/test_target.py::test_top",))
    code, out, err = run(doc)
    assert (code, err) == (0, "")
    assert out == "OK 1 entries, 2 code citations, 1 test citations\n"


# T2 anchor absent


def test_anchor_not_found(run):
    doc = entry("T2ID", code=(("src.py", 4, "NOPE_ANCHOR"),))
    failed(run(doc), ": T2ID: anchor not found")


# T3 anchor ambiguous, even when the cited line matches one occurrence


def test_anchor_ambiguous_even_if_cited_line_matches_one_occurrence(run):
    doc = entry("T3ID", code=(("src.py", 2, "    return 1"),))
    failed(run(doc), ": T3ID: anchor ambiguous (2 occurrences)")


# T4 a unique anchor cited at the wrong line


def test_stale_line_reports_the_actual_line_and_leaves_the_document_unchanged(run, root):
    doc = entry("T4ID", code=(("src.py", 99, "def beta():"),))
    written = write(root, DOC, doc)
    before = written.read_bytes()
    result = run(doc)
    failed(result, ": T4ID: stale line 99, anchor is on line 4")
    assert (root / DOC).read_bytes() == before


# T5 --fix rewrites only the stale number


def test_fix_rewrites_only_the_stale_number_and_exits_0(run, root):
    stale = entry("T5", code=(("src.py", 99, "def beta():"),))
    fixed = entry("T5", code=(("src.py", 4, "def beta():"),))
    write(root, DOC, stale)
    code, out, err = run(stale, "--fix")
    assert err == ""
    assert code == 0
    assert out.startswith("fixed ")
    assert ": T5: 99 -> 4" in out
    assert out.endswith("OK 1 entries, 1 code citations, 1 test citations\n")
    assert (root / DOC).read_text(encoding="utf-8") == fixed


def test_fix_rewrites_the_stale_line_but_still_reports_an_unrelated_error(run, root):
    stale = entry("T5A", code=(("src.py", 99, "def beta():"),))
    stale_fixed = entry("T5A", code=(("src.py", 4, "def beta():"),))
    broken = entry("T5B", code=(("src.py", 1, "NOT_AN_ANCHOR"),))
    write(root, DOC, stale + "\n" + broken)
    code, out, err = run(stale + "\n" + broken, "--fix")
    assert code == 1
    assert ": T5A: 99 -> 4" in out
    assert ": T5B: anchor not found" in err
    assert (root / DOC).read_text(encoding="utf-8") == stale_fixed + "\n" + broken


# T6 unsafe or missing Code paths are errors, never read


def test_unsafe_or_missing_code_paths_are_rejected(run, root, tmp_path):
    outside = write(tmp_path / "outside", "secret.py", "SECRET_TOKEN = 1\n")
    (root / "escape_link").symlink_to(outside.parent)
    doc = "".join([
        entry("MISSING", code=(("does_not_exist.py", 1, "anything"),)),
        "\n",
        entry("DOTDOT", code=(("../outside/secret.py", 1, "SECRET_TOKEN"),)),
        "\n",
        entry("ABS", code=((str(outside), 1, "SECRET_TOKEN"),)),
        "\n",
        entry("SYMLINK", code=(("escape_link/secret.py", 1, "SECRET_TOKEN"),)),
    ])
    err = failed(run(doc),
                 ": MISSING: file not found",
                 ": DOTDOT: path must not contain '..'",
                 ": ABS: path must be relative",
                 ": SYMLINK: path resolves outside the root")
    assert err


# T7 Test citations: missing file, missing function, Class::method found,
# a nested function or a name only in a comment/string rejected, path outside tests/ rejected


def test_test_citation_variants(run):
    doc = entry(
        "T7CASE",
        code=(("src.py", 4, "def beta():"),),
        test=(
            "tests/unit/does_not_exist.py::test_missing_file",
            "tests/unit/test_target.py::test_missing_function",
            "tests/unit/test_target.py::TestThing::test_method",
            "tests/unit/test_target.py::nested",
            "tests/unit/test_target.py::test_ghost",
            "src.py::test_top",
        ),
    )
    err = failed(
        run(doc),
        ": T7CASE: file not found",
        ": T7CASE: function 'test_missing_function' not found at module level",
        ": T7CASE: function 'nested' not found at module level",
        ": T7CASE: function 'test_ghost' not found at module level",
        ": T7CASE: path must be under tests/",
    )
    assert "TestThing.test_method" not in err


# T8 structure errors


def test_structure_errors(run):
    stray = "- **Code:** `src.py:4` — «`def beta():`»\n\n"
    doc = "".join([
        stray,
        entry("NOTEST", test=()),
        "\n",
        entry("NOCODE", code=()),
        "\n",
        entry("NOEN", en_palabras=()),
        "\n",
        entry("TWOEN", en_palabras=("uno.", "dos.")),
        "\n",
        entry("NOSRC", source=()),
        "\n",
        entry("TWOSRC", source=("uno.", "dos.")),
        "\n",
        entry("DUPID"),
        "\n",
        entry("DUPID", title="second"),
    ])
    failed(
        run(doc),
        "-: field line before the first entry heading",
        ": NOTEST: missing 'Test'",
        ": NOCODE: missing 'Code'",
        ": NOEN: missing 'En palabras'",
        ": TWOEN: 'En palabras' appears more than once",
        ": NOSRC: missing 'Source'",
        ": TWOSRC: 'Source' appears more than once",
        ": DUPID: duplicate ID 'DUPID'",
    )


# T9 malformed field lines are errors, not skipped


def test_malformed_field_lines_are_never_skipped(run):
    doc = (
        "### NOGUILL — t\n"
        "- **En palabras:** x.\n"
        "- **Code:** `src.py:4` — def beta():\n"
        "- **Test:** `tests/unit/test_target.py::test_top`\n"
        "- **Source:** AGENTS 1.1\n"
        "\n"
        "### NOCOLON — t\n"
        "- **En palabras:** x.\n"
        "- **Code:** `src.py` — «`def beta():`»\n"
        "- **Test:** `tests/unit/test_target.py::test_top`\n"
        "- **Source:** AGENTS 1.1\n"
        "\n"
        "### ZEROLINE — t\n"
        "- **En palabras:** x.\n"
        "- **Code:** `src.py:0` — «`def beta():`»\n"
        "- **Test:** `tests/unit/test_target.py::test_top`\n"
        "- **Source:** AGENTS 1.1\n"
        "\n"
        "### BACKTICK — t\n"
        "- **En palabras:** x.\n"
        "- **Code:** `src.py:4` — «`def be`ta():`»\n"
        "- **Test:** `tests/unit/test_target.py::test_top`\n"
        "- **Source:** AGENTS 1.1\n"
        "\n"
        "### UNKNOWNF — t\n"
        "- **En palabras:** x.\n"
        "- **Code:** `src.py:4` — «`def beta():`»\n"
        "- **Test:** `tests/unit/test_target.py::test_top`\n"
        "- **Unknown:** something\n"
        "- **Source:** AGENTS 1.1\n"
    )
    failed(
        run(doc),
        ": NOGUILL: malformed Code field",
        ": NOCOLON: malformed Code field",
        ": ZEROLINE: invalid line number '0'",
        ": BACKTICK: malformed Code field",
        ": UNKNOWNF: unknown field 'Unknown'",
    )


# T10 no entries, missing document, invalid UTF-8


def test_no_entries_exits_1(run):
    failed(run("no headings here\n"), "-: document has no entries")


def test_missing_document_exits_2(invoke, root):
    code, out, err = invoke("--root", str(root), "missing.md")
    assert (code, out) == (2, "")
    assert err


def test_invalid_utf8_document_exits_2(invoke, root):
    (root / DOC).write_bytes(b"### X \xe2\x80\x94 t\n\xff\xfe")
    code, out, err = invoke("--root", str(root), DOC)
    assert (code, out) == (2, "")
    assert err


@pytest.mark.parametrize("argv", [["--root", "missing-dir"], ["--bogus"]])
def test_usage_errors_exit_2(invoke, argv):
    with pytest.raises(SystemExit) as raised:
        invoke(*argv)
    assert raised.value.code == 2


# T11 hermeticity: only allowlisted stdlib imports, none of the AGENTS 2.1 primitives


def test_tool_imports_only_the_allowed_standard_library_modules():
    roots = set()
    for node in ast.walk(ast.parse(TOOL.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots, "no import found: the scan would pass on anything"
    assert roots <= ALLOWED_IMPORTS, roots - ALLOWED_IMPORTS


FORBIDDEN_PRIMITIVES = ("fetch(", "axios", "urllib", "requests", "httpx", "socket", "subprocess",
                         "curl", "wget", "aiohttp", "importlib", "os.system", "os.popen")


def test_tool_source_names_no_network_or_process_primitive():
    source = TOOL.read_text(encoding="utf-8")
    for primitive in FORBIDDEN_PRIMITIVES:
        assert primitive not in source, primitive


# T12 the real repository: docs/traceability/TRACEABILITY.md must check out clean


def test_the_real_traceability_document_is_self_consistent(invoke):
    doc_path = REPO_ROOT / "docs" / "traceability" / "TRACEABILITY.md"
    text = doc_path.read_text(encoding="utf-8")
    expected_entries = len(re.findall(r"^### ", text, re.MULTILINE))
    expected_code = len(re.findall(r"^- \*\*Code:\*\*", text, re.MULTILINE))
    expected_test = len(re.findall(r"^- \*\*Test:\*\*", text, re.MULTILINE))
    assert expected_entries > 0

    code, out, err = invoke()

    assert err == ""
    assert code == 0
    assert out == f"OK {expected_entries} entries, {expected_code} code citations, {expected_test} test citations\n"
