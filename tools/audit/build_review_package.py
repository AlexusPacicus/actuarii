"""Build the package a blind review reads, and hold the review lock.

What a review reads comes from the `review` key of .actuarii.json: the package holds the review procedure
(whose citations are not followed), the base documents, the record under review, and the repository files they
cite (one level, never the citations of cited files), read from one commit with `git show`. Denied paths never
enter it: the prefixes of `denied`, every other record under the records directory, and always `.data/` (the audit
trail, the context log and the lock). A prefix denies by string prefix, not by directory.
Citations that do not resolve at the commit are listed, not invented. MANIFEST.json records the
commit, the record, the procedure, the base documents, the denied prefixes, each file's sha256, and the denied and
unresolved citations. Without a configured review, or with an invalid configuration, nothing is built.

While the lock exists, tools/hooks/confine_review_reads.py confines Read, Grep and Glob to the
package. `build --lock` first checks that the reviewer will also start without the project's CLAUDE.md files,
memory and git snapshot, by configuration: its definition (.claude/agents/blind-reviewer.md) has exactly the keys
name, description, tools (Read, Grep, Glob) and omitClaudeMd (true), and includeGitInstructions is false in the first
of .claude/settings.local.json, .claude/settings.json and ~/.claude/settings.json that sets it. Otherwise it writes
one line per unmet guarantee to stderr, writes neither the package nor the lock, and exits 1.

    build_review_package.py build --record <records>/<record>.md --commit <sha> --out <dir> --lock
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
if str(REPO_ROOT) in sys.path:
    import tools
else:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import tools
    finally:
        sys.path.remove(str(REPO_ROOT))

from tools import project_config  # noqa: E402
from tools.project_config import ReviewConfig  # noqa: E402

LOCK_PATH = REPO_ROOT / ".data" / "review_lock.json"
REVIEWER_PATH = REPO_ROOT / ".claude" / "agents" / "blind-reviewer.md"
SETTINGS_PATHS = (
    REPO_ROOT / ".claude" / "settings.local.json",
    REPO_ROOT / ".claude" / "settings.json",
    Path.home() / ".claude" / "settings.json",
)
REVIEWER_FIELDS = {"name": "blind-reviewer", "tools": "Read, Grep, Glob", "omitClaudeMd": "true"}
GIT_KEY = "includeGitInstructions"
FRONT_MATTER_LINE = re.compile(r"([A-Za-z][A-Za-z0-9_-]*):(?: +(.*))?")
ALWAYS_DENIED = (".data/",)
PATH_RE = re.compile(r"(?<![\w./-])[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.*-]+)+")

Reader = Callable[[str], bytes | None]


@dataclass
class Selection:
    files: dict[str, bytes] = field(default_factory=dict)
    denied: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def cited_paths(text: str) -> list[str]:
    return sorted({match.rstrip(".") for match in PATH_RE.findall(text)})


def _is_denied(path: str, docs: tuple[str, ...], review: ReviewConfig) -> bool:
    if path.startswith(f"{review.records}/") and path not in docs:
        return True
    return any(path.startswith(entry) or path == entry.rstrip("/") for entry in (*ALWAYS_DENIED, *review.denied))


def select_files(record: str, read: Reader, review: ReviewConfig) -> Selection:
    if not record.startswith(f"{review.records}/") or record in review.base_docs:
        raise ValueError(f"the record must be a file under {review.records}/ and not a base document, got {record}")
    docs = (*review.base_docs, record)
    selection = Selection()
    for doc in (review.procedure, *docs):
        data = read(doc)
        if data is None:
            raise FileNotFoundError(f"{doc} not found at the reviewed commit")
        selection.files[doc] = data
    cited = sorted({p for doc in docs for p in cited_paths(selection.files[doc].decode("utf-8"))})
    for path in cited:
        if path in docs:
            continue
        if _is_denied(path, docs, review):
            selection.denied.append(path)
            continue
        data = read(path)
        if data is None:
            selection.unresolved.append(path)
        else:
            selection.files[path] = data
    return selection


def write_package(out_dir: Path, selection: Selection, commit: str, record: str, review: ReviewConfig) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    for path, data in selection.files.items():
        target = out_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = {
        "commit": commit,
        "record": record,
        "procedure": review.procedure,
        "base_docs": list(review.base_docs),
        "denied_prefixes": list(review.denied),
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


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("it does not start with a front matter between two --- lines")
    fields: dict[str, str] = {}
    for number, line in enumerate(lines[1:lines.index("---", 1)], start=2):
        match = FRONT_MATTER_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"line {number} is not key: value")
        key = match.group(1)
        if key in fields:
            raise ValueError(f"line {number} repeats the key {key}")
        fields[key] = (match.group(2) or "").strip()
    return fields


def reviewer_gaps(path: Path) -> list[str]:
    try:
        fields = parse_front_matter(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{path}: the blind reviewer's definition does not exist"]
    except (OSError, ValueError) as exc:
        return [f"{path}: the blind reviewer's definition cannot be read as front matter ({exc})"]
    gaps = [f"{path}: key {key} is not allowed in the blind reviewer's definition: it can add context or tools"
            for key in fields if key != "description" and key not in REVIEWER_FIELDS]
    gaps += [f"{path}: key {key} must be {value}"
             for key, value in REVIEWER_FIELDS.items() if fields.get(key) != value]
    if not fields.get("description"):
        gaps.append(f"{path}: key description must be set")
    return gaps


def git_snapshot_gaps(paths: tuple[Path, ...]) -> list[str]:
    unreadable: list[str] = []
    values: list[tuple[Path, object]] = []
    for path in paths:
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, NotADirectoryError):
            continue
        except (OSError, ValueError) as exc:
            unreadable.append(f"{path}: {GIT_KEY} cannot be checked, the file cannot be read as JSON ({exc})")
            continue
        if not isinstance(settings, dict):
            unreadable.append(f"{path}: {GIT_KEY} cannot be checked, the file is not a JSON object")
        elif GIT_KEY in settings:
            values.append((path, settings[GIT_KEY]))
    if unreadable:
        return unreadable
    if not values:
        return [f"{GIT_KEY} must be false and none of {', '.join(str(path) for path in paths)} sets it"]
    path, value = values[0]
    if value is False:
        return []
    return [f"{path}: key {GIT_KEY} must be false, it is {json.dumps(value)}"]


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


def _configured_review() -> ReviewConfig | None:
    try:
        review = project_config.load().review
    except project_config.ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return None
    if review is None:
        sys.stderr.write(
            f"no blind review is configured: set the review key of {project_config.CONFIG_NAME} "
            "(procedure, base_docs, records, denied)\n")
    return review


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
    review = _configured_review()
    if review is None:
        return 1
    gaps = [*reviewer_gaps(REVIEWER_PATH), *git_snapshot_gaps(SETTINGS_PATHS)] if args.lock else []
    if gaps:
        sys.stderr.write("".join(f"{gap}\n" for gap in gaps))
        return 1
    selection = select_files(args.record, git_reader(args.commit), review)
    write_package(args.out, selection, args.commit, args.record, review)
    print(json.dumps({"package": str(args.out.resolve()), "files": sorted(selection.files),
                      "denied": selection.denied, "unresolved": selection.unresolved}, indent=2))
    if args.lock:
        write_lock(LOCK_PATH, args.out)
        print(f"review lock set: {LOCK_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
