"""Verification of the red and green phases of a delegation (tools/audit/verify_red_green.py).

Each case builds a tiny git project under tmp_path (an application module, its tests and a base commit), drives the
script as a child process through tools.audit.run_process with the project as the working directory, and checks the
verdict lines, the exit code and that no worktree and no temporary directory is left behind. Git and pytest start
only through run_process; no test imports subprocess.
"""
import ast
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.audit.run_process import run

SCRIPT = Path(__file__).resolve().parents[2] / 'tools' / 'audit' / 'verify_red_green.py'
LF = chr(10)
TASK = 'fix-value'
TEST_FILE = 'tests/test_app.py'
GUARD = TEST_FILE + '::test_guard'
NEW = TEST_FILE + '::test_new'
ALLOWED_IMPORTS = {'__future__', 'argparse', 'dataclasses', 'os', 'pathlib', 'shutil', 'sys', 'tempfile', 'tools'}


def text(*lines):
    return LF.join(lines) + LF


APP_BASE = text('def other():', "    return 'x'", '', '', 'def value():', '    return 1')
APP_FIXED = APP_BASE.replace('return 1', 'return 2')
TESTS_BASE = text('from app import other', '', '', 'def test_guard():', "    assert other() == 'x'")
TESTS_FINAL = text(
    'from app import other, value', '', '', 'def test_guard():', "    assert other() == 'x'", '', '',
    'def test_new():', '    assert value() == 2',
)
NEWMOD = text('def answer():', '    return 3')


def git(cwd, *args):
    done = run(
        ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', '-c', 'commit.gpgsign=false', *args],
        cwd=cwd,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@dataclass
class Project:
    root: Path
    base: str = ''

    def commit(self, files):
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'change')
        return git(self.root, 'rev-parse', 'HEAD')

    def fixed(self):
        return self.commit({'app.py': APP_FIXED, TEST_FILE: TESTS_FINAL})


@pytest.fixture
def scratch(tmp_path):
    path = tmp_path / 'scratch'
    path.mkdir()
    return path


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    git(root, 'init', '-q')
    created = Project(root)
    created.base = created.commit({'app.py': APP_BASE, 'tests/__init__.py': '', TEST_FILE: TESTS_BASE})
    return created


def contract(project, *tests, task_id=TASK):
    return {
        'schema_version': 'delegation/1',
        'task_id': task_id,
        'title': 'Fix the value',
        'branch': 'fix/value',
        'base_commit': project.base,
        'attribution': None,
        'context': {'task': 'why', 'sources': [{'path': 'notes.md', 'select': [{'clause': '1.1'}]}]},
        'problem': 'The value is wrong.',
        'decisions': [],
        'behaviours': [{'id': 'B1', 'statement': 'The value is 2.'}],
        'tests': [
            {'id': i, 'must_catch': 'a wrong value', 'expectation': e, 'reason': 'not fixed yet'} for i, e in tests
        ],
        'files_may_touch': ['app.py'],
        'files_must_not_touch': [],
        'gates': ['full-suite'],
        'commit_message': 'fix: the value',
        'report_schema': 'delegation-report/2',
    }


def report(commit, *tests, task_id=TASK):
    return {
        'schema_version': 'delegation-report/2',
        'task_id': task_id,
        'commit': commit,
        'tests': [
            {'id': i, 'expectation': e, 'nodeids': ids, 'red_reason': 'not fixed yet', 'catches': 'a wrong value'}
            for i, e, ids in tests
        ],
        'gates': [{'gate': 'full-suite', 'status': 'pass', 'detail': 'ok'}],
        'choices': [],
        'ranges_read_beyond_context': [],
        'not_done': [],
    }


@pytest.fixture
def verify(project, scratch, tmp_path):
    def call(contract_doc, report_doc, cwd=None):
        contract_file = tmp_path / 'contract.json'
        contract_file.write_text(json.dumps(contract_doc), encoding='utf-8')
        done = run(
            [sys.executable, str(SCRIPT), '--contract', str(contract_file)],
            cwd=cwd or project.root,
            env={**os.environ, 'TMPDIR': str(scratch)},
            stdin=report_doc if isinstance(report_doc, str) else json.dumps(report_doc),
            timeout=300,
        )
        assert list(scratch.iterdir()) == []
        assert git(project.root, 'worktree', 'list', '--porcelain').count('worktree ') == 1
        return done

    return call


def refused(done, *reasons):
    assert (done.returncode, done.stdout) == (1, '')
    assert 'refused' in done.stderr
    for reason in reasons:
        assert reason in done.stderr, done.stderr


def verdict(done, code, *lines):
    assert (done.returncode, done.stdout.splitlines()) == (code, list(lines)), done.stderr


# T5 a correct report is accepted, and nothing is left behind


def test_a_correct_report_is_accepted(project, verify):
    commit = project.fixed()
    done = verify(
        contract(project, ('T1', 'red'), ('T2', 'guard')),
        report(commit, ('T1', 'red', [NEW]), ('T2', 'guard', [GUARD])),
    )
    verdict(done, 0, 'T1 red base=fail final=pass OK', 'T2 guard base=pass final=pass OK', 'full-suite final=pass OK')
    assert done.stderr == ''


def test_an_implementers_own_test_is_checked_with_its_own_expectation(project, verify):
    commit = project.fixed()
    done = verify(
        contract(project, ('T1', 'red')),
        report(commit, ('T1', 'red', [NEW]), ('X1', 'guard', [GUARD]), ('X2', 'red', [NEW])),
    )
    verdict(
        done, 0,
        'T1 red base=fail final=pass OK',
        'X1 guard base=pass final=pass OK',
        'X2 red base=fail final=pass OK',
        'full-suite final=pass OK',
    )


def test_a_red_test_that_cannot_be_collected_at_base_is_red(project, verify):
    tests = TESTS_FINAL.replace('from app import other, value', 'from app import other, value' + LF + 'from newmod import answer')
    commit = project.commit({'app.py': APP_FIXED, 'newmod.py': NEWMOD, TEST_FILE: tests})
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [NEW])))
    verdict(done, 0, 'T1 red base=error final=pass OK', 'full-suite final=pass OK')


def test_a_failing_suite_refuses_a_report_whose_tests_are_all_right(project, verify):
    broken = TESTS_FINAL + text('', '', 'def test_other():', '    assert False')
    commit = project.commit({'app.py': APP_FIXED, TEST_FILE: broken})
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [NEW])))
    verdict(done, 1, 'T1 red base=fail final=pass OK', 'full-suite final=fail FAIL')


# T2 a red test that already passes at the base commit is not red


def test_a_red_test_that_passes_at_base_is_refused(project, verify):
    commit = project.fixed()
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [GUARD])))
    verdict(done, 1, 'T1 red base=pass final=pass FAIL', 'full-suite final=pass OK')


# T3 a guard that fails at base, a red test that fails at final, a node id that does not exist, a fix not committed


def test_a_guard_that_fails_at_base_is_refused(project, verify):
    commit = project.fixed()
    done = verify(contract(project, ('T1', 'guard')), report(commit, ('T1', 'guard', [NEW])))
    verdict(done, 1, 'T1 guard base=fail final=pass FAIL', 'full-suite final=pass OK')


def test_a_red_test_that_does_not_pass_at_final_is_refused(project, verify):
    commit = project.commit({TEST_FILE: TESTS_FINAL})
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [NEW])))
    verdict(done, 1, 'T1 red base=fail final=fail FAIL', 'full-suite final=fail FAIL')


def test_a_node_id_that_does_not_exist_is_refused(project, verify):
    commit = project.fixed()
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [TEST_FILE + '::test_missing'])))
    verdict(done, 1, 'T1 red base=usage final=usage FAIL', 'full-suite final=pass OK')


def test_a_fix_only_in_the_working_tree_is_refused(project, verify):
    commit = project.commit({TEST_FILE: TESTS_FINAL})
    (project.root / 'app.py').write_text(APP_FIXED, encoding='utf-8')
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', [NEW])))
    verdict(done, 1, 'T1 red base=fail final=fail FAIL', 'full-suite final=fail FAIL')


def test_a_test_file_only_in_the_working_tree_is_refused(project, verify):
    commit = project.commit({'app.py': APP_FIXED})
    (project.root / 'tests' / 'test_later.py').write_text(TESTS_FINAL, encoding='utf-8')
    done = verify(contract(project, ('T1', 'red')), report(commit, ('T1', 'red', ['tests/test_later.py::test_new'])))
    refused(done, 'tests/test_later.py')


# T4 a report that does not match its contract is refused before anything runs

MISMATCHES = [
    ('a contract test the report lacks', 'T2'),
    ('another expectation', 'expectation'),
    ('another task id', 'task_id'),
    ('a T id the contract lacks', 'T2'),
    ('a test reported twice', 'twice'),
]


@pytest.mark.parametrize('name, reason', MISMATCHES, ids=[name for name, _ in MISMATCHES])
def test_a_report_that_does_not_match_its_contract_is_refused(project, verify, name, reason):
    commit = project.fixed()
    one = ('T1', 'red', [NEW])
    two = ('T2', 'guard', [GUARD])
    cases = {
        'a contract test the report lacks': (contract(project, ('T1', 'red'), ('T2', 'guard')), report(commit, one)),
        'another expectation': (contract(project, ('T1', 'red')), report(commit, ('T1', 'guard', [NEW]))),
        'another task id': (contract(project, ('T1', 'red')), report(commit, one, task_id='other-task')),
        'a T id the contract lacks': (contract(project, ('T1', 'red')), report(commit, one, two)),
        'a test reported twice': (contract(project, ('T1', 'red')), report(commit, one, one)),
    }
    refused(verify(*cases[name]), reason)


def test_a_final_commit_that_is_not_a_descendant_of_base_is_refused(project, verify):
    commit = project.fixed()
    git(project.root, 'switch', '-q', '-c', 'side', project.base)
    side = project.commit({'side.txt': 'x'})
    git(project.root, 'switch', '-q', '-')
    doc = contract(project, ('T1', 'red'))
    refused(verify({**doc, 'base_commit': side}, report(commit, ('T1', 'red', [NEW]))), 'descendant')


def test_a_final_commit_that_is_the_base_commit_is_refused(project, verify):
    refused(verify(contract(project, ('T1', 'red')), report(project.base, ('T1', 'red', [NEW]))), 'base commit')


def test_a_commit_the_repository_does_not_have_is_refused(project, verify):
    refused(verify(contract(project, ('T1', 'red')), report('f' * 40, ('T1', 'red', [NEW]))), 'not a commit')


def test_a_directory_that_is_not_a_repository_is_refused(project, verify, tmp_path):
    plain = tmp_path / 'plain'
    plain.mkdir()
    refused(verify(contract(project, ('T1', 'red')), report('a' * 40, ('T1', 'red', [NEW])), cwd=plain))


# input and usage


def test_a_report_in_the_old_schema_exits_2(project, verify):
    commit = project.fixed()
    old = {**report(commit, ('T1', 'red', [NEW])), 'schema_version': 'delegation-report/1'}
    done = verify(contract(project, ('T1', 'red')), old)
    assert (done.returncode, done.stdout) == (2, '')
    assert 'schema_version' in done.stderr


def test_a_contract_file_that_does_not_exist_exits_2(project, tmp_path):
    done = run([sys.executable, str(SCRIPT), '--contract', str(tmp_path / 'none.json')], cwd=project.root, stdin='{}')
    assert (done.returncode, done.stdout) == (2, '')
    assert 'none.json' in done.stderr


def test_the_contract_option_is_required(project):
    done = run([sys.executable, str(SCRIPT)], cwd=project.root, stdin='{}')
    assert (done.returncode, done.stdout) == (2, '')
    assert '--contract' in done.stderr


def test_the_script_starts_processes_only_through_run_process():
    tree = ast.parse(SCRIPT.read_text(encoding='utf-8'))
    imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported <= ALLOWED_IMPORTS
    assert 'tools' in imported
