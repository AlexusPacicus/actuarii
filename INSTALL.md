# Installing Actuarii

Actuarii installs into an existing git repository. The installer copies the kit into the repository's
`tools/` directory, merges its settings into what is already there, and never overwrites anything:
if a path it would write already holds something else, it stops, lists every conflict and writes
nothing.

## What you need

* macOS or Linux, `git`, and [Claude Code](https://claude.com/claude-code).
* A `python3` (3.9 or later) to run the installer. It uses the standard library only.
* For the Claude Code session: a Python 3.11 environment with `pydantic==2.13.3`. The validator that
  issues receipts needs it, and it runs with the `python3` on your `PATH` when Claude Code starts.

## 1. Get Actuarii

```bash
git clone https://github.com/AlexusPacicus/actuarii.git
```

Install from a clean checkout: the installer copies the working tree of the clone, so a stray file
under its `tools/` would be copied too.

## 2. Check what the installer would do

From the Actuarii clone, with the path of your repository's top level:

```bash
python3 tools/install.py --dry-run /path/to/your/repo
```

It prints what it would write and what it would skip. Nothing is written. Exit status 1 means
conflicts, listed one per line; exit status 2 means the target is not the top level of a git working
tree.

## 3. Install

```bash
python3 tools/install.py /path/to/your/repo
```

It writes:

* `tools/`: the hooks, the validator, the Python shim and the audit tools;
* `.claude/agents/` and `.claude/skills/`: the implementer and blind-reviewer subagents and their skills;
* `.actuarii.json`: an example configuration that governs `AGENTS.md`, `CLAUDE.md`, `.claude/**`,
  `.mcp.json` and `tools/**`;
* `.claude/settings.json`: the hooks and a strict Bash sandbox, merged into your settings;
* `.mcp.json`: the `boundary-validator` server, merged into your servers;
* the git `pre-commit` hook, where git looks for it;
* a `.data/` line in `.gitignore` (the audit trail lives there).

It also warns when your own `~/.claude/settings.json` does not set
`"sandbox": {"allowUnsandboxedCommands": false}`. That value keeps a project's
`.claude/settings.local.json` from turning the sandbox off. The installer never writes your own
settings; add it yourself if you want it.

## 4. Commit what was installed

The Python shim only runs scripts committed in `HEAD`, and the hooks are scripts.

```bash
cd /path/to/your/repo
git add tools .claude .mcp.json .actuarii.json .gitignore
git commit -m "Install Actuarii"
```

The `pre-commit` hook runs on this commit already.

## 5. Prepare the Python environment

Claude Code starts the validator with the `python3` on your `PATH`, so that interpreter needs
`pydantic==2.13.3`. Two ways:

* **Your project's environment,** if `pydantic==2.13.3` fits its other requirements:

  ```bash
  source .venv/bin/activate
  pip install pydantic==2.13.3
  pip check
  ```

* **A separate environment,** if it does not. Then Bash commands in the session (your tests, your
  scripts) also run with this interpreter, so it needs your project's dependencies too:

  ```bash
  python3.11 -m venv ~/.venvs/actuarii
  source ~/.venvs/actuarii/bin/activate
  pip install pydantic==2.13.3
  ```

## 6. Open Claude Code

From the repository's top level, in the shell where that environment is active:

```bash
claude
```

Accept the folder trust and the `boundary-validator` MCP server when asked.

The session starts with an announcement from Actuarii: where its rules come from, the governed paths,
the receipt window, whether the Bash sandbox is on and whether the commit hook is installed. Check that
the sandbox is on and the hook installed.

## 7. What you will see

A write to a governed path without a receipt is denied, and the denial names the rule, the file in the
configuration it comes from, and the call that resolves it. After a receipt for that exact change, the
same write is allowed. Nothing in your prompts needs to mention any of this: the rules are enforced by
the hooks, not by instructions.

## Governing more of your repository

Add patterns to `governed_paths` in `.actuarii.json`, for example `"src/**"`. Then add the matching
entry to `sandbox.filesystem.denyWrite` in `.claude/settings.json` (`"./src"` for `src/**`), so that
Bash cannot write those paths either. The installer does not update `denyWrite` after it has run; this
step is manual.

## Limits

What the kit does not cover is declared in Actuarii's [`AGENTS.md`](AGENTS.md), section 9.
