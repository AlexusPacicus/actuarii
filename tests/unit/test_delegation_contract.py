"""Delegation contract and report schema (tools/audit/delegation_contract.py, AGENTS 6.1).

A delegation is a strict JSON document, not a free-text prompt: every object forbids extra keys, every
property is required and no field has a default (the meaning of `strict` in build_response_format).
Fixtures are built here and the tool is driven through `main`; only the agent-definition guard reads
the repository, and nothing runs a child process or writes a file.
"""

import ast
import copy
import io
import json
import re
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from tools.audit import context_pack
from tools.audit import delegation_contract as dc
from traianus.security.schemas.proposals import build_response_format

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / 'tools' / 'audit' / 'delegation_contract.py'
AGENT = REPO_ROOT / '.claude' / 'agents' / 'engine-implementer.md'
ALLOWED_IMPORTS = {'__future__', 'argparse', 'json', 'pathlib', 're', 'sys', 'typing', 'pydantic', 'tools'}
FORBIDDEN_CALLS = {'open', 'write_text', 'write_bytes', 'mkdir', 'touch', 'unlink', 'eval', 'exec'}
LF = chr(10)
BACKSLASH = chr(92)

BEHAVIOUR = {'id': 'B1', 'statement': 'Extra keys are rejected.'}
TEST = {'id': 'T1', 'must_catch': 'an extra key', 'expectation': 'red', 'reason': 'no schema yet'}
CONTRACT = {
    'schema_version': 'delegation/1',
    'task_id': 'delegation-contract',
    'title': 'Strict delegation schema',
    'branch': 'feat/delegation-contract',
    'base_commit': '651bdf4',
    'attribution': 'Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>',
    'scope': 'tools',
    'context': {
        'task': 'why these sections',
        'sources': [{'path': 'notes.md', 'select': [{'clause': '1.1'}, {'heading': 'Scope'}]}],
    },
    'problem': 'Free-text prompts cannot be checked in code.',
    'decisions': ['Pydantic'],
    'behaviours': [BEHAVIOUR],
    'tests': [TEST],
    'files_may_touch': ['tools/audit/delegation_contract.py'],
    'files_must_not_touch': ['traianus/**'],
    'gates': ['pytest_full', 'ruff_ci'],
    'commit_message': 'feat(tools): delegation contract',
    'report_schema': 'delegation-report/1',
}
REPORT = {
    'schema_version': 'delegation-report/1',
    'task_id': 'delegation-contract',
    'commit': '0123456789abcdef0123456789abcdef01234567',
    'tests': [
        {'id': 'T1', 'red_reason': 'no schema yet', 'catches': 'an extra key'},
        {'id': 'X1', 'red_reason': 'not validated', 'catches': 'a bad path'},
    ],
    'gates': [{'gate': 'pytest_full', 'status': 'pass', 'detail': '1 passed'}],
    'choices': ['picked the first reading'],
    'ranges_read_beyond_context': ['context_pack.py:213-231'],
    'not_done': ['nothing'],
}
DOCS = {'contract': CONTRACT, 'report': REPORT}


def walk(node, path=()):
    yield path, node
    if isinstance(node, dict):
        for key, child in node.items():
            yield from walk(child, path + (key,))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from walk(child, path + (index,))


def at(doc, path):
    for step in path:
        doc = doc[step]
    return doc


def replaced(command, path, value):
    doc = copy.deepcopy(DOCS[command])
    if not path:
        return value
    at(doc, path[:-1])[path[-1]] = value
    return doc


def without(command, path, key):
    doc = copy.deepcopy(DOCS[command])
    del at(doc, path)[key]
    return doc


def with_extra(command, path):
    doc = copy.deepcopy(DOCS[command])
    at(doc, path)['extra'] = 'x'
    return doc


def label(path):
    return '/'.join(str(step) for step in path) or 'top'


def location(path):
    return '.'.join(str(step) for step in path)


def flat(table):
    return [(command, path, value) for command, path, values in table for value in values]


def flat_ids(cases):
    return [f'{command}:{label(path)}:{value!r}' for command, path, value in cases]


NODES = [(command, path) for command, doc in DOCS.items() for path, _ in walk(doc)]
DICTS = [(command, path) for command, path in NODES if isinstance(at(DOCS[command], path), dict)]
MISSING = [(command, path, key) for command, path in DICTS for key in at(DOCS[command], path)]
WRONG_TYPES = {
    str: [1, 1.5, True, None, ['x'], {'a': 'b'}],
    list: ['text', None, 1, {}],
    dict: [['x'], 'text', None, 1],
}
TYPED = [(c, p, bad) for c, p in NODES for bad in WRONG_TYPES[type(at(DOCS[c], p))]
         if not (c == 'contract' and p == ('attribution',) and bad is None)]


@pytest.fixture
def invoke(monkeypatch, capsys):
    def call(main, raw, *argv):
        if isinstance(raw, bytes):
            stream = io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8')
        else:
            stream = io.StringIO(raw if isinstance(raw, str) else json.dumps(raw))
        monkeypatch.setattr(sys, 'stdin', stream)
        code = main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return call


@pytest.fixture
def cli(invoke):
    return lambda raw, *argv: invoke(dc.main, raw, *argv)


def reject(cli, command, doc):
    code, out, err = cli(doc, command)
    assert (code, out) == (1, ''), err
    assert err.strip()
    return err


def accept(cli, command, doc):
    code, out, err = cli(doc, command)
    assert (code, err) == (0, ''), err
    return out


# T1 a valid contract and a valid report pass


@pytest.mark.parametrize('command', ['contract', 'report'])
def test_a_valid_document_passes(cli, command):
    assert accept(cli, command, DOCS[command]) == f'{command} OK task_id=delegation-contract' + LF


def test_a_null_attribution_is_accepted(cli):
    doc = replaced('contract', ('attribution',), None)
    assert accept(cli, 'contract', doc) == 'contract OK task_id=delegation-contract' + LF


def test_the_models_carry_every_field_of_the_documents():
    assert dc.DelegationContract.model_validate(CONTRACT).model_dump() == CONTRACT
    assert dc.DelegationReport.model_validate(REPORT).model_dump() == REPORT


# T2 an extra field is rejected at every level


@pytest.mark.parametrize('command, path', DICTS, ids=[f'{c}:{label(p)}' for c, p in DICTS])
def test_an_extra_key_is_rejected_at_every_level(cli, command, path):
    assert 'extra' in reject(cli, command, with_extra(command, path))


# T3 each required field is required


@pytest.mark.parametrize('command, path, key', MISSING, ids=[f'{c}:{label(p + (k,))}' for c, p, k in MISSING])
def test_each_field_is_required(cli, command, path, key):
    err = reject(cli, command, without(command, path, key))
    assert 'Field required' in err
    assert key in err


# T4 strict types: no coercion


@pytest.mark.parametrize('command, path, bad', TYPED, ids=flat_ids(TYPED))
def test_types_are_not_coerced(cli, command, path, bad):
    reject(cli, command, replaced(command, path, bad))


# T5 patterns, literals and lengths

BAD_VALUES = [
    ('contract', ('task_id',), ['', 'ab', 'a' * 65, 'Abc', '-abc', 'ab_c', 'abc def', 'abc' + LF]),
    ('contract', ('branch',), ['', 'ab', 'a' * 102, 'Feat/x', '-feat', 'feat x', '/feat', 'feat/../x',
                               'feat..x', 'feat/x/', 'feat/x.lock']),
    ('contract', ('base_commit',), ['', 'abcdef', 'a' * 41, 'ABCDEF1', 'ghijklm', '651bdf4 ']),
    ('contract', ('attribution',), ['', 'Co-Authored-By: Claude', 'Co-Authored-By: <a@b.c>',
                                    'Co-Authored-By: A <ab>', 'co-authored-by: A <a@b.c>',
                                    'Co-Authored-By: A <a@b.c>' + LF + 'more']),
    ('contract', ('behaviours', 0, 'id'), ['', 'B', 'b1', 'B100', 'T1']),
    ('contract', ('tests', 0, 'id'), ['', 'T', 't1', 'T100', 'X1', 'B1']),
    ('contract', ('schema_version',), ['', 'delegation/2', 'delegation-report/1']),
    ('contract', ('report_schema',), ['', 'delegation-report/2', 'delegation/1']),
    ('contract', ('scope',), ['', 'docs', 'Tools', 'Client', 'client ']),
    ('contract', ('tests', 0, 'expectation'), ['', 'green', 'RED', 'Manual', 'manual ']),
    ('contract', ('gates', 0), ['', 'ruff', 'pytest', 'MYPY', 'TSC', 'tsc ']),
    ('contract', ('title',), ['', 'x' * 121]),
    ('contract', ('problem',), ['']),
    ('contract', ('commit_message',), ['', 'x' * 101, 'x' * 101 + LF + 'body']),
    ('report', ('schema_version',), ['', 'delegation/1', 'delegation-report/2']),
    ('report', ('task_id',), ['', 'ab', 'Abc', 'a' * 65]),
    ('report', ('commit',), ['', 'a' * 39, 'a' * 41, 'A' * 40, 'g' * 40, '651bdf4']),
    ('report', ('tests', 0, 'id'), ['', 'T', 'Y1', 'x1', 'T100', 'B1']),
    ('report', ('gates', 0, 'gate'), ['', 'ruff', 'pytest', 'TSC', 'tsc ']),
    ('report', ('gates', 0, 'status'), ['', 'ok', 'PASS']),
]
GOOD_VALUES = [
    ('contract', ('task_id',), ['abc', 'a' * 64, 'a1-b2']),
    ('contract', ('branch',), ['abc', 'a' * 101, 'fix/x.y_z-1', 'feat/lock', 'feat/x.locks']),
    ('contract', ('base_commit',), ['abcdef1', 'a' * 40]),
    ('contract', ('behaviours', 0, 'id'), ['B1', 'B99']),
    ('contract', ('tests', 0, 'id'), ['T1', 'T99']),
    ('contract', ('scope',), ['engine']),
    ('contract', ('tests', 0, 'expectation'), ['guard']),
    ('contract', ('gates', 0), ['pytest_model', 'mypy', 'validate_proposal']),
    ('contract', ('title',), ['x', 'x' * 120]),
    ('contract', ('commit_message',), ['x', 'x' * 100, 'subject' + LF + 'y' * 500]),
    ('report', ('commit',), ['a' * 40]),
    ('report', ('gates', 0, 'gate'), ['tsc', 'validate_proposal']),
    ('report', ('tests', 0, 'id'), ['T1', 'X12']),
    ('report', ('gates', 0, 'status'), ['fail', 'not_run']),
]
BAD = flat(BAD_VALUES)
GOOD = flat(GOOD_VALUES)


@pytest.mark.parametrize('command, path, value', BAD, ids=flat_ids(BAD))
def test_a_bad_value_is_rejected_at_its_field(cli, command, path, value):
    assert location(path) in reject(cli, command, replaced(command, path, value))


@pytest.mark.parametrize('command, path, value', GOOD, ids=flat_ids(GOOD))
def test_a_boundary_value_is_accepted(cli, command, path, value):
    accept(cli, command, replaced(command, path, value))


# T6 lists: minimum sizes, unique ids and gates, disjoint file lists

EMPTY_REJECTED = [
    ('contract', ('behaviours',)),
    ('contract', ('tests',)),
    ('contract', ('files_may_touch',)),
    ('contract', ('gates',)),
    ('contract', ('context', 'sources')),
    ('contract', ('context', 'sources', 0, 'select')),
    ('report', ('gates',)),
]
EMPTY_ACCEPTED = [
    ('contract', ('decisions',)),
    ('contract', ('files_must_not_touch',)),
    ('report', ('tests',)),
    ('report', ('choices',)),
    ('report', ('ranges_read_beyond_context',)),
    ('report', ('not_done',)),
]
DUPLICATES = [
    ('behaviours', [BEHAVIOUR, {**BEHAVIOUR, 'statement': 'other'}]),
    ('tests', [TEST, {**TEST, 'must_catch': 'other'}]),
    ('gates', ['ruff_ci', 'ruff_ci']),
]
DISTINCT = [
    ('behaviours', [BEHAVIOUR, {**BEHAVIOUR, 'id': 'B2'}]),
    ('tests', [TEST, {**TEST, 'id': 'T2'}]),
    ('gates', ['ruff_ci', 'mypy']),
]


@pytest.mark.parametrize('command, path', EMPTY_REJECTED, ids=[f'{c}:{label(p)}' for c, p in EMPTY_REJECTED])
def test_an_empty_required_list_is_rejected(cli, command, path):
    assert location(path) in reject(cli, command, replaced(command, path, []))


@pytest.mark.parametrize('command, path', EMPTY_ACCEPTED, ids=[f'{c}:{label(p)}' for c, p in EMPTY_ACCEPTED])
def test_an_empty_optional_list_is_accepted(cli, command, path):
    accept(cli, command, replaced(command, path, []))


@pytest.mark.parametrize('field, value', DUPLICATES, ids=[field for field, _ in DUPLICATES])
def test_duplicate_ids_and_gates_are_rejected(cli, field, value):
    err = reject(cli, 'contract', replaced('contract', (field,), value))
    assert field in err
    assert 'duplicate' in err


@pytest.mark.parametrize('field, value', DISTINCT, ids=[field for field, _ in DISTINCT])
def test_distinct_ids_and_gates_are_accepted(cli, field, value):
    accept(cli, 'contract', replaced('contract', (field,), value))


def test_an_entry_in_both_file_lists_is_rejected(cli):
    doc = replaced('contract', ('files_may_touch',), ['tools/a.py', 'tools/b.py'])
    doc['files_must_not_touch'] = ['tools/b.py', 'docs/**']
    err = reject(cli, 'contract', doc)
    assert 'tools/b.py' in err
    assert 'both' in err


# T7 paths

BAD_PATHS = [
    '', '/', '/etc/passwd', '..', '../x', 'a/../b', 'a/..', 'a..b',
    'a' + BACKSLASH + 'b', BACKSLASH + 'x', '..' + BACKSLASH + 'x', 'C:' + BACKSLASH + 'x',
    'tools/a?.py', 'tools/[ab].py', 'tools/{a,b}.py', 'tools/***/x',
]
GOOD_PATHS = ['tools/audit/x.py', 'tools/**', 'tests/unit/test_*.py', '**/x.md', '.claude/agents/x.md', 'AGENTS.md']
FILE_LISTS = ['files_may_touch', 'files_must_not_touch']


@pytest.mark.parametrize('field', FILE_LISTS)
@pytest.mark.parametrize('bad', BAD_PATHS, ids=repr)
def test_a_bad_path_is_rejected(cli, field, bad):
    assert field + '.0' in reject(cli, 'contract', replaced('contract', (field,), [bad]))


@pytest.mark.parametrize('field', FILE_LISTS)
@pytest.mark.parametrize('good', GOOD_PATHS, ids=repr)
def test_a_relative_path_with_star_wildcards_is_accepted(cli, field, good):
    accept(cli, 'contract', replaced('contract', (field,), [good]))


# T8 the context is what context_pack reads

CLAUSE = {'clause': '1.1'}
SELECTORS = [
    CLAUSE, {'heading': 'Scope'}, {'symbol': 'parse_spec'}, {'paragraph': 'some text'},
    {'match': '^a.*z$'}, {'lines': '1-5'},
]


def source(*selectors, path='notes.md'):
    return {'path': path, 'select': list(selectors)}


def context(*sources, task='why these sections'):
    return {'task': task, 'sources': list(sources)}


CONTEXTS = {
    'unknown selector key': context(source({'section': '1.1'})),
    'two keys in a selector': context(source({'clause': '1.1', 'heading': 'Scope'})),
    'empty selector': context(source({})),
    'empty select': context(source()),
    'empty sources': context(),
    'blank task': context(source(CLAUSE), task=' '),
    'malformed clause': context(source({'clause': 'one'})),
    'reversed lines': context(source({'lines': '5-1'})),
    'malformed lines': context(source({'lines': 'a-b'})),
    'invalid regex': context(source({'match': '('})),
    'empty selector value': context(source({'heading': ''})),
    'multi-line selector value': context(source({'heading': 'a' + LF + 'b'})),
    'multi-line path': context(source(CLAUSE, path='a' + LF + 'b')),
    'empty path': context(source(CLAUSE, path='')),
}


@pytest.mark.parametrize('name', list(CONTEXTS))
def test_a_context_that_context_pack_rejects_is_rejected(cli, name):
    with pytest.raises(context_pack.SpecError):
        context_pack.parse_spec(json.dumps(CONTEXTS[name]))
    assert 'context' in reject(cli, 'contract', replaced('contract', ('context',), CONTEXTS[name]))


@pytest.mark.parametrize('selector', SELECTORS, ids=[next(iter(s)) for s in SELECTORS])
def test_every_selector_kind_is_accepted(cli, selector):
    spec = context(source(selector), source(CLAUSE, path='other.md'))
    context_pack.parse_spec(json.dumps(spec))
    accept(cli, 'contract', replaced('contract', ('context',), spec))


def test_emit_context_prints_a_command_context_pack_serves(cli, invoke, tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'notes.md').write_text('# Scope' + LF + 'the scope text' + LF + LF + '1.1 A clause.' + LF, encoding='utf-8')
    spec = context(source({'heading': 'Scope'}, CLAUSE), task='why ' + chr(233))
    code, out, err = cli(replaced('contract', ('context',), spec), 'contract', '--emit-context')
    lines = out.splitlines()
    assert (code, err) == (0, '')
    assert lines[0] == 'contract OK task_id=delegation-contract'
    assert lines[1] == "python3 tools/audit/context_pack.py <<'EOF'"
    assert lines[3:] == ['EOF']
    assert len(lines) == 4
    assert json.loads(lines[2]) == spec
    code, out, err = invoke(context_pack.main, lines[2], '--root', str(root), '--log', str(tmp_path / 'pack.log'))
    assert (code, err) == (0, '')
    assert 'the scope text' in out
    assert '1.1 A clause.' in out


# T9 the strictness property of the JSON schema, and the model configuration


def schema_objects(node):
    if isinstance(node, dict):
        if 'properties' in node or node.get('type') == 'object':
            yield node
        for child in node.values():
            yield from schema_objects(child)
    elif isinstance(node, list):
        for child in node:
            yield from schema_objects(child)


@pytest.mark.parametrize('model, minimum', [(dc.DelegationContract, 11), (dc.DelegationReport, 3)])
def test_the_json_schema_is_strict_everywhere(model, minimum):
    objects = list(schema_objects(model.model_json_schema()))
    assert len(objects) >= minimum
    for obj in objects:
        assert obj['additionalProperties'] is False
        assert sorted(obj['required']) == sorted(obj['properties'])
        assert all('default' not in prop for prop in obj['properties'].values())


def test_every_model_is_strict_forbidding_and_frozen():
    models = [m for m in vars(dc).values() if isinstance(m, type) and issubclass(m, BaseModel) and m is not BaseModel]
    assert len(models) >= 10
    for model in models:
        config = model.model_config
        assert (config.get('extra'), config.get('strict'), config.get('frozen')) == ('forbid', True, True), model


def test_a_validated_document_cannot_be_reassigned():
    contract = dc.DelegationContract.model_validate(CONTRACT)
    with pytest.raises(ValidationError):
        contract.title = 'other'


# T10 the schema command has the shape of build_response_format


@pytest.mark.parametrize('name, model', [('contract', dc.DelegationContract), ('report', dc.DelegationReport)])
def test_the_schema_command_matches_build_response_format(cli, name, model):
    expected = build_response_format(model, name=model.__name__)
    code, out, err = cli('', 'schema', name)
    assert (code, err) == (0, '')
    assert out == json.dumps(expected, sort_keys=True) + LF


# T11 the command line


def test_every_error_is_listed_as_location_and_message(cli):
    doc = copy.deepcopy(CONTRACT)
    doc.update({'title': 1, 'base_commit': 'XYZ', 'gates': [], 'extra': 'x'})
    doc['behaviours'][0]['id'] = 'bad'
    code, out, err = cli(doc, 'contract')
    assert (code, out) == (1, '')
    lines = err.splitlines()
    assert sorted(line.split(':', 1)[0] for line in lines) == [
        'base_commit', 'behaviours.0.id', 'extra', 'gates', 'title',
    ]
    assert all(': ' in line for line in lines)


@pytest.mark.parametrize('raw', ['', '{', '[]', 'null', '"text"', '{}'])
def test_a_document_that_is_not_a_valid_object_exits_1(cli, raw):
    reject(cli, 'contract', raw)


def test_unreadable_stdin_exits_2_with_nothing_on_stdout(cli):
    code, out, err = cli(bytes([0xFF, 0xFE, 0x7B]), 'contract')
    assert (code, out) == (2, '')
    assert err.strip()


@pytest.mark.parametrize('argv', [
    [], ['bogus'], ['schema'], ['schema', 'other'], ['contract', '--bogus'], ['report', '--emit-context'],
    ['schema', 'contract', 'report'],
])
def test_usage_errors_exit_2(cli, capsys, argv):
    with pytest.raises(SystemExit) as raised:
        cli('', *argv)
    assert raised.value.code == 2
    assert capsys.readouterr().out == ''


def test_nothing_is_written(cli, monkeypatch, tmp_path):
    work = tmp_path / 'cwd'
    work.mkdir()
    monkeypatch.chdir(work)
    for command, doc in DOCS.items():
        cli(doc, command)
        cli({}, command)
    cli(CONTRACT, 'contract', '--emit-context')
    cli('', 'schema', 'contract')
    assert list(work.iterdir()) == []


def test_the_tool_imports_only_the_standard_library_pydantic_and_context_pack():
    tree = ast.parse(TOOL.read_text(encoding='utf-8'))
    imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, 'id', '')
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert imported <= ALLOWED_IMPORTS
    assert not called & FORBIDDEN_CALLS


# T12 JSON strictness: an ambiguous document is an invalid one


@pytest.mark.parametrize('command', ['contract', 'report'])
def test_a_duplicate_key_is_rejected(cli, command):
    raw = json.dumps(DOCS[command])
    err = reject(cli, command, raw[:-1] + ', "task_id": "another-task"}')
    assert err.startswith('$: ')
    assert 'duplicate key' in err


@pytest.mark.parametrize('nested', [
    ('contract', '{"id": "B1",', '{"id": "B1", "id": "B2",'),
    ('contract', '"sources":', '"task": "again", "sources":'),
    ('report', '{"gate": "pytest_full",', '{"gate": "pytest_full", "gate": "mypy",'),
], ids=['behaviour', 'context', 'gate'])
def test_a_nested_duplicate_key_is_rejected(cli, nested):
    command, old, new = nested
    raw = json.dumps(DOCS[command])
    assert old in raw
    assert 'duplicate key' in reject(cli, command, raw.replace(old, new))


@pytest.mark.parametrize('constant', ['NaN', 'Infinity', '-Infinity'])
@pytest.mark.parametrize('command', ['contract', 'report'])
def test_a_non_finite_constant_is_rejected(cli, command, constant):
    doc = DOCS[command]
    raw = json.dumps(doc).replace(json.dumps(doc['task_id']), constant)
    err = reject(cli, command, raw)
    assert err.startswith('$: ')
    assert constant in err


# T13 the agent definition and the tool stay coherent


def test_the_agent_definition_names_the_two_commands_and_the_json_contract(cli):
    text = AGENT.read_text(encoding='utf-8')
    assert text.startswith('---' + LF + 'name: engine-implementer' + LF)
    assert 'tools: Read, Grep, Glob, Edit, Write, Bash, Skill, mcp__boundary-validator__validate_proposal' in text
    for bound in ('**One branch**', '**Only the files the contract lists.**', '**Test first**',
                  '**Gate every governed file**', '**Invariants stay:**', '**Stop at a commit**'):
        assert bound in text
    for needle in ('DelegationContract', 'DelegationReport', 'tools/audit/context_pack.py'):
        assert needle in text
    commands = set(re.findall(r'tools/audit/delegation_contract[.]py ([a-z]+(?: --[a-z-]+)?)', text))
    assert {'contract --emit-context', 'report'} <= commands
    for command in commands:
        argv = command.split()
        assert cli(DOCS.get(argv[0], ''), *argv)[0] == 0, command


# T14 scope client: the gate tsc and manual tests

MANUAL = {**TEST, 'expectation': 'manual'}
SECOND = {**TEST, 'id': 'T2'}
SRC = 'only frontend/src/, not '
ALL_MANUAL = 'every test of a client contract is manual'
ONLY_TSC = 'has exactly the gate tsc'
MANUAL_NEEDS_CLIENT = 'the expectation manual is valid only when the scope is client'
TSC_NEEDS_CLIENT = 'the gate tsc is valid only when the scope is client'
CLIENT_ACCEPTED = [
    {},
    {'files_may_touch': ['frontend/src/a.ts']},
    {'files_may_touch': ['frontend/src/**']},
    {'files_may_touch': ['frontend/src/a/b.tsx', 'frontend/src/c.css']},
    {'tests': [MANUAL, {**SECOND, 'expectation': 'manual'}]},
    {'files_must_not_touch': ['frontend/package.json', 'traianus/**']},
]
CLIENT_BREACHES = [
    ({'files_may_touch': ['frontend/package.json']}, 'files_may_touch', SRC + 'frontend/package.json'),
    ({'files_may_touch': ['frontend/srcx/a.ts']}, 'files_may_touch', SRC + 'frontend/srcx/a.ts'),
    ({'files_may_touch': ['frontend/src']}, 'files_may_touch', SRC + 'frontend/src'),
    ({'files_may_touch': ['traianus/a.py']}, 'files_may_touch', SRC + 'traianus/a.py'),
    ({'files_may_touch': ['frontend/src/a.ts', 'tools/x.py']}, 'files_may_touch', SRC + 'tools/x.py'),
    ({'gates': ['tsc', 'mypy']}, 'gates', ONLY_TSC),
    ({'gates': ['mypy', 'tsc']}, 'gates', ONLY_TSC),
    ({'gates': ['pytest_full']}, 'gates', ONLY_TSC),
    ({'gates': ['ruff_ci', 'mypy']}, 'gates', ONLY_TSC),
    ({'tests': [{**MANUAL, 'expectation': 'red'}]}, 'tests', ALL_MANUAL),
    ({'tests': [{**MANUAL, 'expectation': 'guard'}]}, 'tests', ALL_MANUAL),
    ({'tests': [MANUAL, {**SECOND, 'expectation': 'red'}]}, 'tests', ALL_MANUAL),
]
NOT_CLIENT_BREACHES = [
    ({'tests': [MANUAL]}, 'tests', MANUAL_NEEDS_CLIENT),
    ({'tests': [TEST, {**SECOND, 'expectation': 'manual'}]}, 'tests', MANUAL_NEEDS_CLIENT),
    ({'gates': ['tsc']}, 'gates', TSC_NEEDS_CLIENT),
    ({'gates': ['pytest_full', 'tsc']}, 'gates', TSC_NEEDS_CLIENT),
    ({'gates': ['tsc', 'mypy']}, 'gates', TSC_NEEDS_CLIENT),
]


def client(**fields):
    doc = copy.deepcopy(CONTRACT)
    doc.update(scope='client', tests=[MANUAL], files_may_touch=['frontend/src/map.ts', 'frontend/src/**'],
               gates=['tsc'])
    doc.update(fields)
    return doc


def not_client(scope, **fields):
    return {**copy.deepcopy(CONTRACT), 'scope': scope, **fields}


def error_locations(err):
    return [line.split(': ', 1)[0] for line in err.splitlines()]


def test_a_client_contract_is_accepted_and_survives_the_model(cli):
    accept(cli, 'contract', client())
    assert dc.DelegationContract.model_validate(client()).model_dump() == client()


@pytest.mark.parametrize('fields', CLIENT_ACCEPTED, ids=repr)
def test_a_client_contract_within_its_couplings_is_accepted(cli, fields):
    accept(cli, 'contract', client(**fields))


def test_a_report_may_carry_the_tsc_gate_and_a_manual_test_entry(cli):
    report = replaced('report', ('gates',), [{'gate': 'tsc', 'status': 'pass', 'detail': 'no type errors'}])
    report['tests'] = [{'id': 'T1', 'red_reason': 'manual: the executing agent runs it', 'catches': 'a blank map'}]
    accept(cli, 'report', report)


@pytest.mark.parametrize('fields, where, message', CLIENT_BREACHES, ids=[repr(b[0]) for b in CLIENT_BREACHES])
def test_a_client_contract_outside_its_couplings_is_rejected_at_the_field(cli, fields, where, message):
    err = reject(cli, 'contract', client(**fields))
    assert error_locations(err) == [where]
    assert message in err


@pytest.mark.parametrize('path', ['frontend/src/../package.json', '../frontend/src/a.ts', 'frontend/src/a/../../b.ts'],
                         ids=repr)
def test_a_client_path_that_climbs_out_is_rejected_by_the_path_rule(cli, path):
    err = reject(cli, 'contract', client(files_may_touch=[path]))
    assert error_locations(err) == ['files_may_touch.0']


@pytest.mark.parametrize('scope', ['engine', 'tools'])
@pytest.mark.parametrize('fields, where, message', NOT_CLIENT_BREACHES, ids=[repr(b[0]) for b in NOT_CLIENT_BREACHES])
def test_manual_and_tsc_are_rejected_with_scope_engine_or_tools(cli, scope, fields, where, message):
    err = reject(cli, 'contract', not_client(scope, **fields))
    assert error_locations(err) == [where]
    assert message in err


def test_each_coupling_is_reported_at_its_own_field(cli):
    broken = client(files_may_touch=['tools/x.py'], gates=['mypy'], tests=[TEST])
    assert sorted(error_locations(reject(cli, 'contract', broken))) == ['files_may_touch', 'gates', 'tests']
    mixed = not_client('tools', gates=['tsc'], tests=[MANUAL])
    assert sorted(error_locations(reject(cli, 'contract', mixed))) == ['gates', 'tests']


@pytest.mark.parametrize('scope', ['engine', 'tools'])
def test_an_engine_or_tools_contract_keeps_red_and_guard_tests_and_every_earlier_gate(cli, scope):
    gates = ['pytest_full', 'pytest_model', 'ruff_ci', 'mypy', 'validate_proposal']
    accept(cli, 'contract', not_client(scope, tests=[TEST, {**SECOND, 'expectation': 'guard'}], gates=gates))


def test_the_agent_definition_states_the_client_scope():
    text = AGENT.read_text(encoding='utf-8')
    _, front, body = text.split('---' + LF, 2)
    description = next(line for line in front.splitlines() if line.startswith('description: '))
    opening = body.split('First action', 1)[0]
    for part in (description, opening):
        assert 'engine, repository-tooling or client change' in part
        assert 'frontend/src/**' in part
    bullet = body[body.index('- **Client scope**'):].split(LF + '- ', 1)[0]
    for needle in ('`tsc`', 'npm --prefix frontend run typecheck', 'npm install', 'package.json', 'manual',
                   'browser', 'test-first', 'pytest'):
        assert needle in bullet
