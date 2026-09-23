"""Build the package a blind instrument review reads, and hold the review lock.

The package holds the review procedure (the instrument-audit skill, whose citations are not
followed) and exactly what docs/methodology/instrument-audit/definitions.md allows: the three base
documents, the record under review, and the repository files they cite (one level, never the
citations of cited files), read from one commit with `git show`. Denied paths never enter it: the
entries of definitions.md "Not allowed", the dev log, and every other record under
docs/methodology/instrument-audit/.
Citations that do not resolve at the commit are listed, not invented. MANIFEST.json records the
commit, the record, each file's sha256, and the denied and unresolved citations.

While the lock exists, tools/hooks/confine_review_reads.py confines Read, Grep and Glob to the
package, so blindness holds by construction.

    build_review_package.py build --record docs/methodology/instrument-audit/K6.md --commit <sha> --out <dir> --lock
    build_review_package.py unlock
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCK_PATH = REPO_ROOT / ".data" / "review_lock.json"
AUDITS = "docs/methodology/instrument-audit/"
PROCEDURE = ".claude/skills/instrument-audit/SKILL.md"
BASE_DOCS = (
    "docs/methodology/instrument-audit/definitions.md",
    "docs/methodology/instrument-audit/derivations.md",
    "docs/methodology/instrument-audit/contracts.md",
)
DENIED = (
    "frontend/POC.md",
    "docs/adrs/ADR-026-",
    "traianus/geometry/spatial_observables.py",
    "data/spinoza/telemetry/",
    "docs/LEDGER.md",
    "docs/development/",
    ".data/",
)
PATH_RE = re.compile(r"(?<![\w./-])[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.*-]+)+")

Reader = Callable[[str], bytes | None]


@dataclass
class Selection:
    files: dict[str, bytes] = field(default_factory=dict)
    denied: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def cited_paths(text: str) -> list[str]:
    return sorted({match.rstrip(".") for match in PATH_RE.findall(text)})


def _is_denied(path: str, docs: tuple[str, ...]) -> bool:
    if path.startswith(AUDITS) and path not in docs:
        return True
    return any(path.startswith(entry) or path == entry.rstrip("/") for entry in DENIED)


def select_files(record: str, read: Reader) -> Selection:
    if not record.startswith(AUDITS) or record in BASE_DOCS:
        raise ValueError(f"the record must be a file under {AUDITS}, got {record}")
    docs = (*BASE_DOCS, record)
    selection = Selection()
    for doc in (PROCEDURE, *docs):
        data = read(doc)
        if data is None:
            raise FileNotFoundError(f"{doc} not found at the reviewed commit")
        selection.files[doc] = data
    cited = sorted({p for doc in docs for p in cited_paths(selection.files[doc].decode("utf-8"))})
    for path in cited:
        if path in docs:
            continue
        if _is_denied(path, docs):
            selection.denied.append(path)
            continue
        data = read(path)
        if data is None:
            selection.unresolved.append(path)
        else:
            selection.files[path] = data
    return selection


def write_package(out_dir: Path, selection: Selection, commit: str, record: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    for path, data in selection.files.items():
        target = out_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = {
        "commit": commit,
        "record": record,
        "files": {p: hashlib.sha256(d).hexdigest() for p, d in selection.files.items()},
        "denied": selection.denied,
        "unresolved": selection.unresolved,
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def write_lock(lock_path: Path, package: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"package": str(package.resolve())}) + "\n", encoding="utf-8")


def clear_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def git_reader(commit: str) -> Reader:
    def read(path: str) -> bytes | None:
        spec = f"{commit}:{path}"
        kind = subprocess.run(["git", "cat-file", "-t", spec], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=False)
        if kind.returncode != 0 or kind.stdout.strip() != "blob":
            return None
        return subprocess.run(["git", "show", spec], cwd=REPO_ROOT,
                              capture_output=True, check=True).stdout
    return read


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--record", required=True)
    build.add_argument("--commit", required=True)
    build.add_argument("--out", required=True, type=Path)
    build.add_argument("--lock", action="store_true")
    sub.add_parser("unlock")
    args = parser.parse_args(argv)
    if args.command == "unlock":
        clear_lock(LOCK_PATH)
        print(f"review lock cleared: {LOCK_PATH}")
        return 0
    selection = select_files(args.record, git_reader(args.commit))
    write_package(args.out, selection, args.commit, args.record)
    print(json.dumps({"package": str(args.out.resolve()), "files": sorted(selection.files),
                      "denied": selection.denied, "unresolved": selection.unresolved}, indent=2))
    if args.lock:
        write_lock(LOCK_PATH, args.out)
        print(f"review lock set: {LOCK_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
