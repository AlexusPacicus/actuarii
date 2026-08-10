"""Active impact scanner for refactorings (OSS Readiness Fase 0).

Before moving a file, run:

    python tools/audit/check_impact.py traianus/security/validator.py

It reports, via `git grep`, every tracked reference to (a) the exact path,
(b) the basename and (c) the stem of the target file, so the atomic move can
list every file that must be updated in the same commit.
"""
import argparse
import os
import subprocess
import sys


def _git_grep(repo_root: str, pattern: str) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "grep", "-n", "-I", "-F", "--", pattern],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return [f"ERROR: git not available while searching {pattern!r}"]
    if proc.returncode not in (0, 1):
        return [f"ERROR: git grep failed for {pattern!r}: {proc.stderr.strip()}"]
    return [ln for ln in proc.stdout.splitlines() if ln]


def scan(target: str, repo_root: str = ".") -> dict[str, list[str]]:
    target = target.replace(os.sep, "/")
    if target.startswith("./"):
        target = target[2:]
    basename = target.rsplit("/", 1)[-1]
    stem = basename.rsplit(".", 1)[0]
    return {
        "path": [h for h in _git_grep(repo_root, target) if not h.startswith(f"{target}:")],
        "basename": _git_grep(repo_root, basename),
        "stem": _git_grep(repo_root, stem),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("target", help="file to move, relative to repo root")
    parser.add_argument("--repo-root", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)

    hits = scan(args.target, args.repo_root)
    total = sum(len(v) for v in hits.values())
    print(f"Impact map for {args.target!r} — {total} reference(s) found.\n")
    for label, lines in hits.items():
        print(f"[{label}]")
        if lines:
            for ln in lines:
                print(f"  {ln}")
        else:
            print("  (no hits)")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
