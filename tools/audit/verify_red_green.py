"""Verifies in code that the tests of a delegation are red at its base commit and green at its final one.

Test first is a convention while the `red_reason` of a report is the implementer's word. This script
takes the proof from pytest instead.

    python3 tools/audit/verify_red_green.py --contract contract.json < report.json

`contract.json` holds the DelegationContract and stdin the DelegationReport (delegation-report/2); both are parsed
with the models of delegation_contract.py. The repository is the git repository of the current directory. Before
running anything it checks that the task_id is the same, that every test of the contract is in the report with the
contract's expectation, that the report has no T id the contract lacks (X ids are the implementer's own) and that
report.commit is a strict descendant of the contract's base_commit.

Then, in detached git worktrees under a new temporary directory, removed afterwards:

* at report.commit each test id runs on its own with its node ids, and then the whole suite (`pytest tests`);
  every test id and the suite must pass (pytest exit 0). The committed tree is verified, not the working tree.
* at the base commit the test files that hold the node ids are copied in from report.commit, nothing else, and each
  test id runs on its own: a `red` test must not pass there (pytest exit 1, or 2 for an error while collecting),
  a `guard` must pass (exit 0). Exit 4 (usage) or 5 (nothing collected) on either side means that the node id does
  not exist as written, and fails; but pytest also answers 4 to a node id whose module fails to import, so at base
  a 4 reruns the files of the test id without their node ids, and the exit 2 of that run stands for the error.

Output: one line per test id (`T1 red base=fail final=pass OK`), then `full-suite final=pass OK`. Exit 0 only when
every line is OK; exit 1 when a line is FAIL, when the verification is refused (`refused: <reason>` on stderr) or
when a cleanup failed; exit 2 when an input is unreadable or invalid or the usage is wrong. Every process starts
through tools.audit.run_process, with the pytest executable that sits next to the interpreter running this script.
A verification that cannot be made is a refusal, never a pass.

Not verified: that a red test fails for the reason the report gives (only that it does not pass at base); the
conftest.py and other support files of the base commit, which are not replaced; and whatever the other gates of the
contract claim beyond the full suite.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
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

from tools.audit import run_process
from tools.audit.delegation_contract import DelegationContract, DelegationReport, Invalid, parse

GIT_TIMEOUT = 120.0
TEST_TIMEOUT = 900.0
SUITE_TIMEOUT = 3600.0
TIMED_OUT = run_process.subprocess.TimeoutExpired
OUTCOMES = {0: "pass", 1: "fail", 2: "error", 4: "usage", 5: "none"}
RED_AT_BASE = {1, 2}
SUITE_TAIL = 20


class Refused(Exception):
    """A verification that cannot succeed, with its reason."""


@dataclass(frozen=True)
class Row:
    test_id: str
    expectation: str
    base: int
    final: int

    @property
    def ok(self) -> bool:
        if self.final != 0:
            return False
        return self.base in RED_AT_BASE if self.expectation == "red" else self.base == 0

    def line(self) -> str:
        verdict = "OK" if self.ok else "FAIL"
        return f"{self.test_id} {self.expectation} base={outcome(self.base)} final={outcome(self.final)} {verdict}"


def outcome(code: int) -> str:
    return OUTCOMES.get(code, f"exit{code}")


def _run(argv: list[str], cwd: Path, timeout: float = GIT_TIMEOUT) -> run_process.Result:
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    try:
        return run_process.run(argv, cwd=cwd, env=env, timeout=timeout)
    except (OSError, UnicodeDecodeError, TIMED_OUT) as exc:
        raise Refused(f"`{' '.join(argv)}` did not complete: {exc}") from exc


def _git(root: Path, *args: str) -> str:
    result = _run(["git", "-C", str(root), *args], root)
    if result.returncode != 0:
        raise Refused(f"`git {' '.join(args)}` exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def _commit(root: Path, ref: str) -> str:
    result = _run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], root)
    if result.returncode != 0:
        raise Refused(f"{ref} is not a commit of this repository")
    return result.stdout.strip()


def _check_match(contract: DelegationContract, report: DelegationReport) -> None:
    if report.task_id != contract.task_id:
        raise Refused(f"task_id {report.task_id!r} is not the contract's {contract.task_id!r}")
    reported: dict[str, str] = {}
    for test in report.tests:
        if test.id in reported:
            raise Refused(f"test {test.id} is reported twice")
        reported[test.id] = test.expectation
    expected = {test.id: test.expectation for test in contract.tests}
    for test_id, expectation in expected.items():
        if test_id not in reported:
            raise Refused(f"contract test {test_id} is not in the report")
        if reported[test_id] != expectation:
            raise Refused(
                f"test {test_id}: expectation {reported[test_id]!r} in the report, {expectation!r} in the contract"
            )
    for test_id in reported:
        if test_id.startswith("T") and test_id not in expected:
            raise Refused(f"report test {test_id} is not in the contract")


def _worktree(root: Path, path: Path, commit: str, created: list[Path]) -> Path:
    _git(root, "worktree", "add", "--detach", str(path), commit)
    created.append(path)
    return path


def _copy_test_files(root: Path, commit: str, tree: Path, report: DelegationReport) -> None:
    paths = sorted({nodeid.split("::", 1)[0] for test in report.tests for nodeid in test.nodeids})
    for path in paths:
        content = _git(root, "show", f"{commit}:{path}")
        target = tree / path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        except OSError as exc:
            raise Refused(f"cannot place {path} in the base worktree: {exc}") from exc


def _base_code(pytest: Path, tree: Path, nodeids: list[str]) -> int:
    code = _run([str(pytest), *nodeids], tree, TEST_TIMEOUT).returncode
    if code != 4:
        return code
    files = sorted({nodeid.split("::", 1)[0] for nodeid in nodeids})
    return 2 if _run([str(pytest), *files], tree, TEST_TIMEOUT).returncode == 2 else code


def _verify(
    contract: DelegationContract, report: DelegationReport, root: Path, scratch: Path, created: list[Path]
) -> tuple[list[str], bool]:
    _check_match(contract, report)
    pytest = Path(sys.executable).with_name("pytest")
    if not pytest.is_file():
        raise Refused(f"{pytest} does not exist: pytest must sit next to the interpreter that runs this script")
    base = _commit(root, contract.base_commit)
    final = _commit(root, report.commit)
    if base == final:
        raise Refused("the report's commit is the base commit")
    ancestry = _run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, final], root)
    if ancestry.returncode == 1:
        raise Refused(f"{final} is not a descendant of the base commit {base}")
    if ancestry.returncode != 0:
        raise Refused(f"`git merge-base --is-ancestor` exited {ancestry.returncode}: {ancestry.stderr.strip()}")
    final_tree = _worktree(root, scratch / "final", final, created)
    base_tree = _worktree(root, scratch / "base", base, created)
    _copy_test_files(root, final, base_tree, report)
    rows = [
        Row(
            test.id,
            test.expectation,
            _base_code(pytest, base_tree, test.nodeids),
            _run([str(pytest), *test.nodeids], final_tree, TEST_TIMEOUT).returncode,
        )
        for test in report.tests
    ]
    suite = _run([str(pytest), "tests"], final_tree, SUITE_TIMEOUT)
    if suite.returncode != 0:
        tail = suite.stdout.splitlines()[-SUITE_TAIL:]
        sys.stderr.write("".join(f"  {line}\n" for line in tail))
    suite_ok = suite.returncode == 0
    lines = [row.line() for row in rows]
    lines.append(f"full-suite final={outcome(suite.returncode)} {'OK' if suite_ok else 'FAIL'}")
    return lines, suite_ok and all(row.ok for row in rows)


def _attempt(
    contract: DelegationContract, report: DelegationReport, root: Path, scratch: Path, created: list[Path]
) -> int:
    try:
        lines, ok = _verify(contract, report, root, scratch, created)
    except Refused as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 1
    sys.stdout.write("".join(f"{line}\n" for line in lines))
    return 0 if ok else 1


def _cleanup(root: Path, scratch: Path, created: list[Path]) -> list[str]:
    problems = []
    for path in created:
        try:
            _git(root, "worktree", "remove", "--force", str(path))
        except Refused as exc:
            problems.append(str(exc))
    try:
        shutil.rmtree(scratch)
    except OSError as exc:
        problems.append(f"cannot delete {scratch}: {exc}")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", required=True, help="the DelegationContract file; the report is read from stdin")
    args = parser.parse_args(argv)
    try:
        contract_raw = Path(args.contract).read_text(encoding="utf-8")
        report_raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"input is not readable: {exc}\n")
        return 2
    try:
        contract = parse(contract_raw, DelegationContract)
        report = parse(report_raw, DelegationReport)
    except Invalid as exc:
        sys.stderr.write("".join(f"{error}\n" for error in exc.errors))
        return 2
    try:
        root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    except Refused as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="verify-red-green-"))
    created: list[Path] = []
    try:
        code = _attempt(contract, report, root, scratch, created)
    finally:
        problems = _cleanup(root, scratch, created)
    for problem in problems:
        sys.stderr.write(f"cleanup failed: {problem}\n")
    return 1 if problems else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
