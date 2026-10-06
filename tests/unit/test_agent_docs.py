"""The agent documents (AGENTS.md, .claude/agents, the skills of both tools) agree with each other.

Everything is read as text; nothing is imported from the kit and nothing is written.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / 'AGENTS.md'
CLAUDE_SKILLS = REPO_ROOT / '.claude' / 'skills'
OPENCODE_SKILLS = REPO_ROOT / '.opencode' / 'skills'
LF = chr(10)


def front_matter(path):
    text = path.read_text(encoding='utf-8')
    assert text.startswith('---' + LF), path
    return text.split('---' + LF, 2)[1]


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


def test_the_skills_of_both_tools_are_the_same_set_and_identical():
    assert skill_names(CLAUDE_SKILLS) == skill_names(OPENCODE_SKILLS)
    for name in skill_names(CLAUDE_SKILLS):
        assert (CLAUDE_SKILLS / name / 'SKILL.md').read_bytes() == (OPENCODE_SKILLS / name / 'SKILL.md').read_bytes(), name


def test_no_skill_or_subagent_names_traianus():
    paths = [path for root in (REPO_ROOT / '.claude', REPO_ROOT / '.opencode') for path in root.rglob('*.md')]
    assert paths
    for path in paths:
        assert 'traianus' not in path.read_text(encoding='utf-8').lower(), path
