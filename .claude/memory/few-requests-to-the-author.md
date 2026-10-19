---
name: few-requests-to-the-author
description: When designing a change or a contract, count the steps that fall to the author and look for the design that does not need them; in Bash, only commands on the list, without variables, cd or loops
metadata:
  type: feedback
---

The sandbox leaves to the person everything that touches governed paths outside the receipt channel: `merge`,
`switch`, `restore`, deleting, reconnecting the MCP server, copying the `pre-commit` again. Each one is a request to
the author.

**Why:** on 2026-10-09 the author pointed out that there were too many requests; the contract was redesigned so that
the conversion was done by the installer, which the person already runs (`docs/DEVLOG.md`).

**How to apply:** in every contract, list the person's steps and look for the design that avoids them. If `main` has
not moved since the branch left it, advance it by fast-forward inside the sandbox (`git branch -f main <branch>` and
`git switch main`) instead of asking for a merge. Related: [[author]].

**Bash:** every call that asks is a request. On 2026-10-15 the author pointed out that every call asked: a bare
`"Bash"` in `ask` covered the read-only list of AGENTS 7.1, because Claude Code evaluates deny, then ask, then allow
(permissions documentation, checked on 2026-10-15). Without it, 231 of the 352 calls of the main chat of the 14th
would still have asked: 80 for the form of the command (variables, `cd`, loops), 84 for read tools outside the list
and 67 because they wrote. ADR-022 removed the bare `"Bash"` and widened the list. One command per call, from the
root, with literal paths of the project or the scratchpad, without variables, `cd`, loops or `$(...)`; files are
read with `Read`, which does not ask.
