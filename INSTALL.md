# Installing Actuarii

Actuarii installs into an existing git repository with one command. The installer copies the kit into
the repository's `tools/` directory, merges its settings into what is already there, and never
overwrites anything: if a path it would write already holds something else, it stops, lists every
conflict and writes nothing.

## What you need

* macOS or Linux, `git`, and [Claude Code](https://claude.com/claude-code).
* A `python3` (3.9 or later) to run the installer. It uses the standard library only.
* A Python environment for the session, **outside your repository**. Claude Code starts the validator
  that issues receipts with the `python3` on its `PATH`, and the validator needs `pydantic==2.13.3`.
  Bash commands in the session (your tests, your scripts) run with that interpreter too, so it also
  needs your project's dependencies.

Why outside: the hooks, the validator and the commit hooks run outside the sandbox, with the
`python3` they find on the `PATH`. An environment inside the repository, such as a `.venv` there, is a
place the agent can write, and code written there would run outside the sandbox at every call of a
gate.

Two repositories take part: the **Actuarii clone**, where the installer comes from, and **your
repository**, where the kit goes. The examples write them as `~/src/actuarii` and `~/src/your-repo`.
Those paths are placeholders: replace each one with where that repository is on your machine.

## 1. Get Actuarii

Clone it next to your repository, never inside it:

```bash
cd ~/src
git clone https://github.com/AlexusPacicus/actuarii.git
```

Install from a clean checkout: the installer copies the working tree of the clone, so a stray file
under its `tools/` would be copied too.

## 2. Prepare the environment

Create it outside your repository and activate it in the shell you will install from and start
Claude Code from:

```bash
python3.11 -m venv ~/.venvs/actuarii
source ~/.venvs/actuarii/bin/activate
```

Install your project's dependencies there as your project says. `pydantic` can wait: the installer
checks it and offers to install it.

## 3. Install

In that same shell, run the installer from the Actuarii clone. Its one argument is the top level of
**your repository**, never the Actuarii clone:

```bash
cd ~/src/actuarii
python3 tools/install.py ~/src/your-repo
```

It asks at most three questions:

1. **Which other paths to govern.** The kit always governs `AGENTS.md`, `CLAUDE.md`, `.claude/**`,
   `.mcp.json` and `tools/**`. Give one path per line, a file (`src/app.py`) or a directory followed by
   `/**` (`src/**`), and an empty line to finish. Each path goes into `governed_paths` and gets its
   `denyWrite` entry, so that Bash cannot write it either.
2. **Whether to install `pydantic==2.13.3`,** only when the interpreter the validator will start with
   lacks it. The question names the interpreter and the exact `pip` command. It is never asked for an
   interpreter or an environment inside your repository.
3. **Whether to commit what it installed,** as `Install Actuarii`. The commit holds exactly the files
   the installer wrote, nothing else you had staged, and the hooks it installed run on it (see step 4).

The first question comes before anything is written; the other two come after the report, and only
when they apply. An answer is `y` or `yes`; anything else, or just Enter, is no.

It writes:

* `tools/`: the hooks, the validator, the Python shim and the audit tools;
* `.claude/agents/` and `.claude/skills/`: the implementer and blind-reviewer subagents and their skills;
* `.actuarii.json`: the configuration, with the paths you chose;
* `.claude/settings.json`: the permission perimeter, the hooks, `includeGitInstructions: false` and a
  strict Bash sandbox with a `denyWrite` entry per governed path, merged into your settings;
* `.mcp.json`: the `boundary-validator` server, merged into your servers;
* the git `pre-commit` and `commit-msg` hooks, where git looks for them;
* a `.data/` line in `.gitignore` (the audit trail lives there).

Then it reports which interpreter the validator will start with and whether it has the pinned
`pydantic`, and ends with the next steps.

To see what it would do without writing anything, add `--dry-run`: it asks nothing and ends with
`dry run: nothing was written`.

Exit status 1 means conflicts (listed one per line, nothing written), or a write, `pip` or the commit
that failed; exit status 2 means the target is not the top level of a git working tree, is the clone
itself, or a `--govern` path was refused. `no such directory` means the path you gave does not exist:
check that it is your repository's path, not the one from the example.

It also warns when your own `~/.claude/settings.json` does not set
`"sandbox": {"allowUnsandboxedCommands": false}`. That value keeps a project's
`.claude/settings.local.json` from turning the sandbox off. The installer never writes your own
settings; add it yourself if you want it.

### Without questions

For a script or the CI, `--no-input` asks nothing, and the flags give the answers:

```bash
python3 tools/install.py --no-input --govern 'src/**' --install-pydantic --commit ~/src/your-repo
```

`--govern` may be repeated. Without `--install-pydantic` it runs no `pip`, and without `--commit` it
makes no commit.

## 4. Commit, if the installer did not

The Python shim only runs scripts committed in `HEAD`, and the hooks are scripts. If you answered no
to the last question, make the commit in a terminal, before you open Claude Code: inside a session
the shim is first on the `PATH`, and it would refuse the commit hooks, which are not in `HEAD` yet.

```bash
cd ~/src/your-repo
git add tools .claude .mcp.json .actuarii.json .gitignore
git commit -m "Install Actuarii"
```

The hooks run on this commit already. Its message ends with one `Actuarii-Record` line per governed
file, saying `changed outside the channel`: the installer wrote them, not an agent through the gate.

## 5. Open Claude Code

From the repository's top level, in the shell where the environment is active:

```bash
claude
```

Accept the folder trust and the `boundary-validator` MCP server when asked.

The session starts with an announcement from Actuarii: where its rules come from, the governed paths,
the receipt window, whether the Bash sandbox is on and whether the commit hook is installed. Check that
the sandbox is on and the hook installed.

## 6. What you will see

A write to a governed path without a receipt is denied, and the denial names the rule, the file in the
configuration it comes from, and the call that resolves it. After a receipt for that exact change, the
same write is allowed. Nothing in your prompts needs to mention any of this: the rules are enforced by
the hooks, not by instructions.

Every commit that changes a governed file carries its record at the end of the message:

```
Actuarii-Record: matches: src/app.py
Actuarii-Rationale: Why the change was made, as the agent gave it in its proposal.
Actuarii-Record: changed outside the channel: AGENTS.md
```

`matches` means that the writes the gate allowed lead from the file at `HEAD` to what the commit
holds; the `Actuarii-Rationale` lines are the reasons of their receipts. `changed outside the channel`
means that something else changed the file: you, an editor, a tool the gate does not see.

## Governing more of your repository later

Run the installer again with the new paths:

```bash
cd ~/src/actuarii
python3 tools/install.py --govern 'docs/**' ~/src/your-repo
```

It keeps the paths it governed before, adds the new ones to `governed_paths` and their entries to
`denyWrite`, and writes nothing else that is already in place.

## Limits

What the kit does not cover is declared in Actuarii's [`AGENTS.md`](AGENTS.md), section 9.
