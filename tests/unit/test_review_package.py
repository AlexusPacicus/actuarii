"""Review package builder (tools/audit/build_review_package.py).

A blind review reads a package that holds exactly what the review configuration allows: the procedure, the base
documents, the record, and the files they cite; denied paths never enter it. The procedure, the base documents,
the records directory and the denied prefixes come from the `review` key of .actuarii.json, never from the builder.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from tools import project_config
from tools.audit import build_review_package
from tools.audit.build_review_package import (
    cited_paths,
    clear_lock,
    select_files,
    write_lock,
    write_package,
)

ROOT = Path(__file__).resolve().parents[2]
RECORD = "audit/K6.md"
PROCEDURE = "skills/review.md"
BASE_DOCS = ("audit/definitions.md", "audit/derivations.md", "audit/contracts.md")
REVIEW = {
    "procedure": PROCEDURE,
    "base_docs": list(BASE_DOCS),
    "records": "audit",
    "denied": ["frontend/POC.md", "adrs/ADR-26-", "engine/prior.py", "data/telemetry/", "bridges/", "dev/"],
}


def _configure(config_file, review=REVIEW):
    config_file({
        "schema": "actuarii-config/1", "governed_paths": ["a"], "python_script_dirs": [],
        "contract_registry": None, "review": review, "receipt_window_seconds": 60,
    })
    return project_config.load().review


@pytest.fixture
def review(config_file):
    return _configure(config_file)


def _repo(extra=None):
    files = {
        "audit/definitions.md":
            b"Operator engine/polar.py (:235-237)\n"
            b"Not allowed frontend/POC.md; adrs/ADR-26-*\n",
        "audit/derivations.md": b"verified by tests/unit/test_derivations.py\n",
        "audit/contracts.md": b"see audit/R4.md and data/refapp/K6_result.json\n",
        RECORD: b"Script: tools/experiments/k6.py; tests/unit/test_k6.py.\n"
                b"Also engine/prior.py and dev/DEVLOG.md\n",
        "engine/polar.py": b"operator\n",
        "tests/unit/test_derivations.py": b"derivations\n",
        "tools/experiments/k6.py": b"script\n",
        "tests/unit/test_k6.py": b"tests\n",
        "frontend/POC.md": b"hypothesis\n",
        "audit/R4.md": b"other record\n",
        "engine/prior.py": b"prior result\n",
        "dev/DEVLOG.md": b"log\n",
        PROCEDURE: b"procedure, cites tools/hooks/anything.py\n",
    }
    files.update(extra or {})
    return files.get


def test_cited_paths_extracts_repo_paths_without_line_suffixes():
    text = ("see engine/polar.py:235-237, `tests/unit/x.py`; "
            "adrs/ADR-26-*.\nand polar.py:58 (bare, ignored)")
    assert cited_paths(text) == [
        "adrs/ADR-26-*",
        "engine/polar.py",
        "tests/unit/x.py",
    ]


def test_select_files_includes_base_record_and_one_level_of_citations(review):
    selection = select_files(RECORD, _repo(), review)
    assert set(selection.files) == {
        PROCEDURE,
        *BASE_DOCS,
        RECORD,
        "engine/polar.py",
        "tests/unit/test_derivations.py",
        "tools/experiments/k6.py",
        "tests/unit/test_k6.py",
    }


def test_the_procedure_and_the_base_documents_are_the_configured_ones(config_file):
    other = {"procedure": "p/other.md", "base_docs": ["audit/only.md"], "records": "audit", "denied": []}
    reader = _repo({"p/other.md": b"other procedure\n", "audit/only.md": b"only base\n"})
    selection = select_files(RECORD, reader, _configure(config_file, other))
    assert {"p/other.md", "audit/only.md", RECORD} <= set(selection.files)
    assert PROCEDURE not in selection.files
    assert "audit/definitions.md" not in selection.files


def test_denied_citations_never_enter_the_package(review):
    selection = select_files(RECORD, _repo(), review)
    for path in ("frontend/POC.md", "audit/R4.md", "adrs/ADR-26-*", "engine/prior.py", "dev/DEVLOG.md"):
        assert path not in selection.files
        assert path in selection.denied


def test_bare_directory_citation_of_denied_entry_is_denied(review):
    extra = {RECORD: b"See data/telemetry for prior audit context.\n"}
    selection = select_files(RECORD, _repo(extra), review)
    assert "data/telemetry" in selection.denied
    assert "data/telemetry" not in selection.unresolved


def test_a_cited_file_under_a_denied_directory_never_enters_the_package(review):
    extra = {
        RECORD: b"See bridges/BRIDGES.md for background.\n",
        "bridges/BRIDGES.md": b"tension gate question\n",
    }
    selection = select_files(RECORD, _repo(extra), review)
    assert "bridges/BRIDGES.md" not in selection.files
    assert "bridges/BRIDGES.md" in selection.denied


def test_the_audit_trail_is_denied_even_when_no_prefix_is_configured(config_file):
    extra = {
        RECORD: b"See .data/boundary_validator_audit.db, .data/review_lock.json and .data/x/y.\n",
        ".data/boundary_validator_audit.db": b"trail\n",
        ".data/review_lock.json": b"lock\n",
    }
    selection = select_files(RECORD, _repo(extra), _configure(config_file, {**REVIEW, "denied": []}))
    for path in (".data/boundary_validator_audit.db", ".data/review_lock.json", ".data/x/y"):
        assert path in selection.denied
        assert path not in selection.files
        assert path not in selection.unresolved


def test_every_other_record_is_denied_even_when_no_prefix_is_configured(config_file):
    selection = select_files(RECORD, _repo(), _configure(config_file, {**REVIEW, "denied": []}))
    assert "audit/R4.md" in selection.denied
    assert "audit/R4.md" not in selection.files


def test_a_prefix_without_a_slash_denies_by_string_prefix_not_by_directory(config_file):
    extra = {RECORD: b"cites adrs/ADR-26-x.md, adrs/ADR-27-x.md and engine/prior_results.py\n",
             "adrs/ADR-26-x.md": b"a\n", "adrs/ADR-27-x.md": b"b\n", "engine/prior_results.py": b"c\n"}
    review = _configure(config_file, {**REVIEW, "denied": ["adrs/ADR-26-", "engine/prior"]})
    selection = select_files(RECORD, _repo(extra), review)
    assert set(selection.denied) >= {"adrs/ADR-26-x.md", "engine/prior_results.py"}
    assert "adrs/ADR-27-x.md" in selection.files


def test_missing_citations_are_reported_not_invented(review):
    selection = select_files(RECORD, _repo(), review)
    assert "data/refapp/K6_result.json" in selection.unresolved
    assert "data/refapp/K6_result.json" not in selection.files


def test_citations_of_cited_files_are_not_followed(review):
    extra = {"tools/experiments/k6.py": b"imports tools/experiments/deeper.py\n",
             "tools/experiments/deeper.py": b"deeper\n"}
    assert "tools/experiments/deeper.py" not in select_files(RECORD, _repo(extra), review).files


def test_missing_base_document_raises(review):
    reader = _repo({"audit/contracts.md": None})
    with pytest.raises(FileNotFoundError, match="contracts.md"):
        select_files(RECORD, reader, review)


def test_missing_procedure_raises(review):
    with pytest.raises(FileNotFoundError, match="review.md"):
        select_files(RECORD, _repo({PROCEDURE: None}), review)


@pytest.mark.parametrize("record", ["frontend/POC.md", "audit2/K6.md", "audit", "audit/definitions.md"])
def test_the_record_must_be_a_file_under_the_records_directory_and_not_a_base_document(review, record):
    with pytest.raises(ValueError, match="audit/"):
        select_files(record, _repo(), review)


def test_write_package_copies_bytes_and_manifest(review, tmp_path):
    selection = select_files(RECORD, _repo(), review)
    out = tmp_path / "pkg"
    write_package(out, selection, commit="abc1234", record=RECORD, review=review)
    for path, data in selection.files.items():
        assert (out / path).read_bytes() == data
    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["commit"] == "abc1234" and manifest["record"] == RECORD
    assert manifest["files"] == {p: hashlib.sha256(d).hexdigest() for p, d in selection.files.items()}
    assert manifest["denied"] == selection.denied
    assert manifest["unresolved"] == selection.unresolved
    assert manifest["procedure"] == PROCEDURE
    assert manifest["base_docs"] == list(BASE_DOCS)
    assert manifest["denied_prefixes"] == REVIEW["denied"]


def test_write_package_refuses_an_existing_directory(review, tmp_path):
    out = tmp_path / "pkg"
    out.mkdir()
    with pytest.raises(FileExistsError):
        write_package(out, select_files(RECORD, _repo(), review), commit="abc1234", record=RECORD, review=review)


def test_lock_round_trip(tmp_path):
    lock = tmp_path / "review_lock.json"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    write_lock(lock, pkg)
    assert json.loads(lock.read_text())["package"] == str(pkg.resolve())
    clear_lock(lock)
    assert not lock.exists()


# the builder reads the configuration of the working tree when it builds


@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.setattr(build_review_package, "LOCK_PATH", tmp_path / "lock" / "review_lock.json")
    monkeypatch.setattr(build_review_package, "git_reader", lambda commit: _repo())

    def build(*extra):
        return build_review_package.main(
            ["build", "--record", RECORD, "--commit", "abc1234", "--out", str(tmp_path / "pkg"), *extra])

    return build


def test_building_from_the_configuration_writes_the_package_and_the_lock(config_file, cli, tmp_path, capsys):
    _configure(config_file)
    assert cli("--lock") == 0
    manifest = json.loads((tmp_path / "pkg" / "MANIFEST.json").read_text())
    assert manifest["procedure"] == PROCEDURE and manifest["record"] == RECORD
    assert (tmp_path / "lock" / "review_lock.json").exists()
    assert "review lock set" in capsys.readouterr().out


@pytest.mark.parametrize("with_file", [False, True], ids=["no-file", "review-null"])
def test_without_a_configured_review_the_builder_names_the_key_and_writes_nothing(
        config_file, cli, tmp_path, capsys, with_file):
    if with_file:
        _configure(config_file, None)
    assert cli("--lock") == 1
    err = capsys.readouterr().err
    assert "review" in err and ".actuarii.json" in err
    assert not (tmp_path / "pkg").exists()
    assert not (tmp_path / "lock").exists()


@pytest.mark.parametrize("content", ["{", '{"schema": "other"}'])
def test_with_an_invalid_configuration_the_builder_reports_the_error_and_writes_nothing(
        config_file, cli, tmp_path, capsys, content):
    config_file(content)
    with pytest.raises(project_config.ConfigError) as error:
        project_config.load()
    assert cli("--lock") == 1
    assert str(error.value) in capsys.readouterr().err
    assert not (tmp_path / "pkg").exists()
    assert not (tmp_path / "lock").exists()


def test_unlock_works_without_reading_the_configuration(config_file, monkeypatch, tmp_path):
    lock = tmp_path / "review_lock.json"
    lock.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(build_review_package, "LOCK_PATH", lock)
    config_file("{")
    assert build_review_package.main(["unlock"]) == 0
    assert not lock.exists()


# the builder and its hook name no project: the rules live in the configuration


@pytest.mark.parametrize("module", ["audit/build_review_package.py", "hooks/confine_review_reads.py"])
def test_the_builder_and_the_hook_cite_no_clause_and_no_project(module):
    source = (ROOT / "tools" / module).read_text(encoding="utf-8")
    assert "AGENTS" not in source
    assert "traianus" not in source.lower()


def test_the_header_of_the_confinement_tests_cites_no_clause():
    header = ast.get_docstring(ast.parse(
        (ROOT / "tests" / "security" / "test_review_confinement.py").read_text(encoding="utf-8")))
    assert "AGENTS" not in header and "traianus" not in header.lower()


@pytest.mark.parametrize("name", ["AUDITS", "PROCEDURE", "BASE_DOCS", "DENIED"])
def test_the_builder_keeps_no_constants_of_a_methodology(name):
    assert not hasattr(build_review_package, name)
