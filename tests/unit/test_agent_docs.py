"""The agent documents (AGENTS.md, .claude/agents, the skills of both tools) agree with each other.

Everything is read as text; nothing is imported from the kit and nothing is written.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / 'AGENTS.md'
REVIEWER = REPO_ROOT / '.claude' / 'agents' / 'blind-reviewer.md'
EXAMPLE_AUDITOR = REPO_ROOT / 'examples' / 'traianus' / 'agents' / 'instrument-auditor.md'
CLAUDE_SKILLS = REPO_ROOT / '.claude' / 'skills'
OPENCODE_SKILLS = REPO_ROOT / '.opencode' / 'skills'
LF = chr(10)


def front_matter(path):
    text = path.read_text(encoding='utf-8')
    assert text.startswith('---' + LF), path
    return text.split('---' + LF, 2)[1]


def fields(path):
    return [tuple(line.partition(': ')[::2]) for line in front_matter(path).splitlines()]


def blocks(path):
    body = path.read_text(encoding='utf-8').split('---' + LF, 2)[2]
    return [' '.join(block.split()) for block in body.split(LF + LF)]


def rules(root):
    text = (root / 'blind-review' / 'SKILL.md').read_text(encoding='utf-8')
    return ' '.join(text.split('## Rules' + LF, 1)[1].split())


def skill_names(root):
    return {path.name for path in root.iterdir() if path.is_dir()}


def test_every_subagent_that_agents_md_names_exists_with_its_name():
    names = set(re.findall(r'[.]claude/agents/([a-z0-9-]+)[.]md', AGENTS_MD.read_text(encoding='utf-8')))
    assert names
    for name in names:
        path = REPO_ROOT / '.claude' / 'agents' / (name + '.md')
        assert path.is_file(), path
        assert 'name: ' + name in front_matter(path).splitlines(), path


def test_the_blind_reviewer_is_read_only_by_construction():
    tools = [line for line in front_matter(REPO_ROOT / '.claude' / 'agents' / 'blind-reviewer.md').splitlines()
             if line.startswith('tools:')]
    assert tools == ['tools: Read, Grep, Glob']


def test_the_blind_reviewer_starts_without_claude_md_memory_skills_servers_or_hooks():
    pairs = fields(REVIEWER)
    assert sorted(key for key, _ in pairs) == ['description', 'name', 'omitClaudeMd', 'tools']
    values = dict(pairs)
    assert values['name'] == 'blind-reviewer'
    assert values['description']
    assert values['tools'] == 'Read, Grep, Glob'
    assert values['omitClaudeMd'] == 'true'


def test_the_blind_reviewer_says_its_context_has_no_project_files_and_stops_if_it_has_them():
    found = blocks(REVIEWER)
    indexes = [i for i, block in enumerate(found) if 'git snapshot' in block]
    assert len(indexes) == 1, 'one paragraph must say the context starts without the git snapshot'
    index = indexes[0]
    paragraph = found[index]
    assert not paragraph.startswith('-')
    for phrase in ('CLAUDE.md', 'memory', 'delegation message', 'expected result', 'prior result',
                   'blindness statement', 'stop'):
        assert phrase in paragraph, phrase
    assert 'You read a review package' in found[index - 1]
    assert found[index + 1].startswith('Output, in this order')


def test_the_skills_of_both_tools_are_the_same_set_and_identical():
    assert skill_names(CLAUDE_SKILLS) == skill_names(OPENCODE_SKILLS)
    for name in skill_names(CLAUDE_SKILLS):
        assert (CLAUDE_SKILLS / name / 'SKILL.md').read_bytes() == (OPENCODE_SKILLS / name / 'SKILL.md').read_bytes(), name


def test_no_skill_or_subagent_names_traianus():
    paths = [path for root in (REPO_ROOT / '.claude', REPO_ROOT / '.opencode') for path in root.rglob('*.md')]
    assert paths
    for path in paths:
        assert 'traianus' not in path.read_text(encoding='utf-8').lower(), path


@pytest.mark.parametrize('root', [CLAUDE_SKILLS, OPENCODE_SKILLS], ids=['claude', 'opencode'])
def test_the_blind_review_skill_states_what_holds_and_what_is_declared(root):
    text = rules(root)
    assert 'by construction' not in text.lower()
    for held in ('confine_review_reads.py', 'omitClaudeMd', 'includeGitInstructions', 'build --lock', 'refuses'):
        assert held in text, held
    for declared in ('delegation message', 'managed-policy', '2.1.271'):
        assert declared in text, declared
    assert 'Audit rules live in the package' in text


def test_the_example_auditor_starts_without_claude_md_too():
    assert ('omitClaudeMd', 'true') in fields(EXAMPLE_AUDITOR)
