# Claude's memory in Actuarii

Memory under code (author's decision, 2026-10-13):
* one file per memory in `.claude/memory/`, with this index, which `CLAUDE.md` loads when each session opens;
* every write asks for a receipt (`.claude/**` is governed), `Bash` does not touch it (the sandbox protects
  `.claude/`) and git keeps every version;
* Claude Code's automatic memory (`~/.claude/projects/…/memory/`) is off in this project: `autoMemoryEnabled:
  false` in `.claude/settings.json` (ADR-010). It is a setting, not a denial: a `.claude/settings.local.json` or the
  variable `CLAUDE_CODE_DISABLE_AUTO_MEMORY` can turn it back on;
* it will be the corpus of the first pilot of the agent memory of phase 4 (`docs/ROADMAP.md` §4).

Each memory has the format of Claude Code's memory: frontmatter with `name`, `description` and `metadata.type`
(`user`, `feedback`, `project` or `reference`). Nothing is kept that the repository, the DEVLOG or the register
already records. The memory is written in English (ADR-032), and so are its file names (ADR-035).

- [How the author works](author.md) — the author decides; simple explanations with one recommendation; technical claims are proved by running them.
- [Ask when an answer is ambiguous](ask-when-ambiguous.md) — an ambiguous answer is not a decision of the author.
- [Few requests to the author](few-requests-to-the-author.md) — count the steps that fall to the author and look for the design that avoids them; in `Bash`, only commands on the list, without variables, `cd` or loops.
