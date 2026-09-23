"""Review package builder (tools/audit/build_review_package.py).

A blind review reads a package that holds exactly what definitions.md allows: the three base
documents, the record, and the files they cite; denied paths never enter it.
"""

import hashlib
import json
from pathlib import Path

import pytest

from tools.audit.build_review_package import (
    BASE_DOCS,
    DENIED,
    PROCEDURE,
    cited_paths,
    clear_lock,
    select_files,
    write_lock,
    write_package,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = "docs/methodology/instrument-audit/K6.md"


def _repo(extra=None):
    files = {
        "docs/methodology/instrument-audit/definitions.md":
            b"Operator traianus/geometry/polar_projector.py (:235-237)\n"
            b"Not allowed frontend/POC.md; docs/adrs/ADR-026-*\n",
        "docs/methodology/instrument-audit/derivations.md": b"verified by tests/unit/test_audit_derivations.py\n",
        "docs/methodology/instrument-audit/contracts.md": b"see docs/methodology/instrument-audit/R4.md and data/refapp/K6_result.json\n",
        RECORD: b"Script: tools/experiments/k6.py; tests/unit/test_k6.py.\n"
                b"Also traianus/geometry/spatial_observables.py and docs/development/DEVLOG.md\n",
        "traianus/geometry/polar_projector.py": b"operator\n",
        "tests/unit/test_audit_derivations.py": b"derivations\n",
        "tools/experiments/k6.py": b"script\n",
        "tests/unit/test_k6.py": b"tests\n",
        "frontend/POC.md": b"hypothesis\n",
        "docs/methodology/instrument-audit/R4.md": b"other record\n",
        "traianus/geometry/spatial_observables.py": b"prior result\n",
        "docs/development/DEVLOG.md": b"log\n",
        PROCEDURE: b"procedure, cites tools/hooks/anything.py\n",
    }
    files.update(extra or {})
    return files.get


def test_cited_paths_extracts_repo_paths_without_line_suffixes():
    text = ("see traianus/geometry/polar_projector.py:235-237, `tests/unit/x.py`; "
            "docs/adrs/ADR-026-*.\nand polar_projector.py:58 (bare, ignored)")
    assert cited_paths(text) == [
        "docs/adrs/ADR-026-*",
        "tests/unit/x.py",
        "traianus/geometry/polar_projector.py",
    ]


def test_select_files_includes_base_record_and_one_level_of_citations():
    selection = select_files(RECORD, _repo())
    assert set(selection.files) == {
        PROCEDURE,
        *BASE_DOCS,
        RECORD,
        "traianus/geometry/polar_projector.py",
        "tests/unit/test_audit_derivations.py",
        "tools/experiments/k6.py",
        "tests/unit/test_k6.py",
    }


def test_denied_citations_never_enter_the_package():
    selection = select_files(RECORD, _repo())
    for path in ("frontend/POC.md", "docs/methodology/instrument-audit/R4.md", "docs/adrs/ADR-026-*",
                 "traianus/geometry/spatial_observables.py", "docs/development/DEVLOG.md"):
        assert path not in selection.files
        assert path in selection.denied


def test_bare_directory_citation_of_denied_entry_is_denied():
    extra = {RECORD: b"See data/spinoza/telemetry for prior audit context.\n"}
    selection = select_files(RECORD, _repo(extra))
    assert "data/spinoza/telemetry" in selection.denied
    assert "data/spinoza/telemetry" not in selection.unresolved


def test_missing_citations_are_reported_not_invented():
    selection = select_files(RECORD, _repo())
    assert "data/refapp/K6_result.json" in selection.unresolved
    assert "data/refapp/K6_result.json" not in selection.files


def test_citations_of_cited_files_are_not_followed():
    extra = {"tools/experiments/k6.py": b"imports tools/experiments/deeper.py\n",
             "tools/experiments/deeper.py": b"deeper\n"}
    assert "tools/experiments/deeper.py" not in select_files(RECORD, _repo(extra)).files


def test_missing_base_document_raises():
    reader = _repo({"docs/methodology/instrument-audit/contracts.md": None})
    with pytest.raises(FileNotFoundError, match="contracts.md"):
        select_files(RECORD, reader)


def test_missing_procedure_raises():
    with pytest.raises(FileNotFoundError, match="SKILL.md"):
        select_files(RECORD, _repo({PROCEDURE: None}))


def test_record_must_be_under_audits():
    with pytest.raises(ValueError, match="docs/methodology/instrument-audit/"):
        select_files("frontend/POC.md", _repo())


def test_write_package_copies_bytes_and_manifest(tmp_path):
    selection = select_files(RECORD, _repo())
    out = tmp_path / "pkg"
    write_package(out, selection, commit="abc1234", record=RECORD)
    for path, data in selection.files.items():
        assert (out / path).read_bytes() == data
    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["commit"] == "abc1234" and manifest["record"] == RECORD
    assert manifest["files"] == {p: hashlib.sha256(d).hexdigest() for p, d in selection.files.items()}
    assert manifest["denied"] == selection.denied
    assert manifest["unresolved"] == selection.unresolved


def test_write_package_refuses_an_existing_directory(tmp_path):
    out = tmp_path / "pkg"
    out.mkdir()
    with pytest.raises(FileExistsError):
        write_package(out, select_files(RECORD, _repo()), commit="abc1234", record=RECORD)


def test_lock_round_trip(tmp_path):
    lock = tmp_path / "review_lock.json"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    write_lock(lock, pkg)
    assert json.loads(lock.read_text())["package"] == str(pkg.resolve())
    clear_lock(lock)
    assert not lock.exists()


def test_denylist_covers_every_entry_of_definitions_not_allowed():
    text = (REPO_ROOT / "docs/methodology/instrument-audit/definitions.md").read_text()
    not_allowed = text.split("Not allowed", 1)[1]
    for entry in ("frontend/POC.md", "docs/adrs/ADR-026-",
                  "traianus/geometry/spatial_observables.py", "data/spinoza/telemetry/",
                  "docs/LEDGER.md"):
        assert entry in not_allowed
        assert any(entry.startswith(d) or d.startswith(entry) for d in DENIED)
