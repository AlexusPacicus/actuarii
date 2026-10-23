# Claude Code's sandbox as the lower layer (research, a draft for the author)

Claude's draft, 2026-10-07. It answers the research agreed once the check of primitives moved to `ast`: that list
stops the honest agent, but it is not a boundary; the boundary is where the code runs. Source: the official
documentation, "Configure the sandboxed Bash tool" (code.claude.com/docs/en/sandboxing), read on 2026-10-07, with
Claude Code 2.1.291 installed. §1 to §6 say what the documentation says; §8 is what was then tested on this machine.

Condensed and translated from Spanish on 2026-10-20 (ADR-033). The full draft, in Spanish, is in the history: this
file at `750c61f`.

## 1. The two questions

**Does it cut the network of `Bash` and of what it launches?** Yes, according to the documentation. The operating
system (Seatbelt on macOS, a separate network namespace with bubblewrap on Linux) leaves each `Bash` command, and each
process it launches, with no direct route to the network. It can only go out through a local proxy that checks the
host name against a list of allowed domains, which starts empty. What is not TCP (UDP, QUIC, ICMP) does not go out.
This covers the case that matters: code the agent wrote and then ran with `pytest` or a script from `Bash` runs inside
the sandbox, however it was written (`getattr`, `sys.modules`, `pickle`, a `.sh`).

**Can it keep `Bash` from writing the governed paths?** Yes, according to the documentation.
`sandbox.filesystem.denyWrite` denies writing, at the level of the operating system, to `Bash` commands and their
child processes, inside the working directory. The sandbox also protects on its own `.claude/` (settings, skills,
agents, hooks), `.mcp.json`, the shell's start-up files, and `.git`'s hooks and configuration, with no exception
possible.

## 2. What the sandbox does not cover

* **The file tools** (`Read`, `Edit`, `Write`): they follow the permission rules, not the sandbox. The kit's gates
  cover them (receipt, literal quote, primitives in the gate).
* **The hooks and the MCP servers:** they run outside, with all of the user's access. They are the kit's code,
  governed.
* **The commands the person types** with `!`: outside the sandbox. It is the person.
* **Reading:** by default almost the whole machine can be read, credentials included, unless `denyRead` or
  `credentials` is configured.
* **Native Windows and OpenCode:** there is no sandbox. The perimeters of `.claude/settings.json` and of
  `opencode.jsonc` would stop being the same (AGENTS 7.1), which has to be declared.

## 3. The ways out to close

* **The retry without the sandbox** (`dangerouslyDisableSandbox`): Claude can ask to repeat a command outside. Closed
  with `allowUnsandboxedCommands: false`.
* **Starting without the sandbox:** if a dependency is missing or the platform does not support it, Claude Code runs
  commands without the sandbox, without warning. Closed with `failIfUnavailable: true`.
* **Automatic approval:** with the sandbox on, `Bash` commands are approved on their own by default
  (`autoAllowBashIfSandboxed`), which would change the permission perimeter. Kept with
  `autoAllowBashIfSandboxed: false`, which a repository can set.
* **`excludedCommands`:** each pattern takes commands out of the sandbox. The kit must not bring any.
* **Where each key holds:** the documentation says that a `false` for `allowUnsandboxedCommands` in the user's
  settings, in `--settings` or in the managed settings holds even if the project sets `true`. It does not say whether a
  `false` in `.claude/settings.json` alone is enough; that is tested (§7, S4).

## 4. What would change in the kit

* **The `sandbox` key** in `.claude/settings.json` (§6), with a `denyWrite` that repeats the governed paths of
  `.actuarii.json`: either the installer generates it, or a test checks that the two match.
* **Two declared limits close,** if the tests confirm it: writes to governed paths through `Bash`, and, in part,
  forged logs. With the validator's database in `denyWrite`, `Bash` can no longer write receipts. The rest of `.data/`
  cannot be denied, because the agent runs from `Bash` the scripts that write the context log and the review lock;
  those stay forgeable, and it is declared.
* **The shell heuristics become warnings:** with the network and the governed writes cut by the system, a way around
  the shim no longer reaches anything that matters. The `Bash` hook and the list of primitives stay as early
  warnings; the boundary is the sandbox.
* **The cost for daily work:** `git switch`, `git merge`, `git restore` and `git checkout` write in governed paths, so
  they fail inside the sandbox. Either the person runs them (`!`), or an `excludedCommands` pattern sends them out of
  the sandbox to the usual permission flow. The author decides (§9).
* **A path the sandbox does not close:** git writes only to `.git/objects` and to the index when it creates commits.
  With `git hash-object -w`, `git update-index` and `git commit`, an agent can put content for a governed path into
  the history without writing the file, and a later `git merge` or `git checkout` by the person brings it into the
  tree. It is declared.
* **The blind review does not change** (author, 2026-10-07): the sandbox's `denyRead` affects only `Bash`, and the
  blind reviewer has only `Read`, `Grep` and `Glob`, which the kit's hook confines.

## 5. What the settings reference fixes (code.claude.com/docs/en/settings-reference, 2026-10-07)

* **Paths:** in the project's settings, `./path` or a path without a prefix resolves from the project's root; `/path`
  is absolute.
* **Scope:** `enabled`, `failIfUnavailable`, `allowUnsandboxedCommands`, `autoAllowBashIfSandboxed` and
  `filesystem.denyWrite` can be set in the project's `.claude/settings.json`.
* **Precedence:** `.claude/settings.local.json` is above `.claude/settings.json`, so a local file could turn the
  sandbox off. Not during the session: the `ConfigChange` hook blocks changes of settings, the sandbox protects
  `.claude/` from `Bash`, and `.claude/**` is governed for `Edit` and `Write`. Before the session opens, it could (A10,
  declared).
* **The reinforcement the project cannot give:** an `allowUnsandboxedCommands: false` in `~/.claude/settings.json`
  holds even if the project or the local file sets `true` (since 2.1.285). It is a change to the user's own
  configuration, made by the person.
* **Lists add up:** `denyWrite` combines across files.

**Note (2026-10-20):** the draft said the README would recommend that reinforcement. It is `INSTALL.md` that
recommends it, and the installer warns when it is missing.

## 6. The change proposed for `.claude/settings.json`

The `sandbox` key, added at the end of the root object. The permission perimeter does not change:
`autoAllowBashIfSandboxed: false` keeps the question for every `Bash` command that is not in `allow`.

```json
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "autoAllowBashIfSandboxed": false,
    "filesystem": {
      "denyWrite": [
        "./AGENTS.md",
        "./CLAUDE.md",
        "./tests",
        "./tools",
        "./opencode.jsonc",
        "./pyproject.toml",
        "./.actuarii.json",
        "./.data/boundary_validator_audit.db"
      ]
    }
  }
```

The edit goes through the gate, with its receipt, and applies from a new session. Afterwards, if §7 passes: a test
that `denyWrite` covers every governed path of `.actuarii.json`, except `.claude/**` and `.mcp.json`, which the
sandbox protects on its own; AGENTS §9 with the limits that close and those that remain; and the decision on
`git switch` and `git merge`. Applied on 2026-10-07 (`582cd65`).

**Note (2026-10-20):** the exemption of `.claude/**` and `.mcp.json` ended on 2026-10-14 (`b8b912a`). Every governed
path has its `denyWrite` entry, with no exemption, and the test checks it.

## 7. Test plan (committed before running it)

With the configuration of §6 in `.claude/settings.json`, applied in a new session. Each case says what is expected;
what comes out differently is noted as it is.

| Case | Command (Claude runs it, not the person) | Expected |
|---|---|---|
| S1 network | `curl --noproxy '*' https://example.com` | Fails: the host does not resolve |
| S1b network | A committed script of `tools/` that opens a socket to a host that is not allowed | Fails |
| S2 write | `touch tests/zz_probe` and `touch tools/zz_probe` | `Operation not permitted` |
| S2b write | `touch docs/zz_probe` | Works (not governed); removed afterwards |
| S3 audit trail | Write to `.data/boundary_validator_audit.db` (for example, `touch`) | `Operation not permitted`; `context_pack.py` still writes its log |
| S4 retry | Claude asks to repeat S2 with `dangerouslyDisableSandbox` | Ignored: still in the sandbox |
| S5 approval | A command that writes in `docs/` | Asks, as today |
| S6 kit | The hooks (a governed `Edit` without a receipt), the MCP server and the session announcement | Work as today |
| S7 suite | `pytest tests` inside the sandbox | Green, with the same number of tests |
| S8 git | `git commit` on a branch; `git switch` to another that changes `tools/` | The commit works; the `switch` fails |
| S9 no sandbox | (cannot be provoked on macOS without touching the system) | Left as declared |

**Decision rule:** if S1, S2, S3 and S4 come out as expected, v0.1 relies on the sandbox for the network, the
processes and the writes through `Bash`, and the shell heuristics are declared. If S4 fails with the project's
settings alone, the user is asked to set `allowUnsandboxedCommands: false` in their own settings, and the installer
checks it. If S1 or S2 fails, it is declared and goes to v0.2.

## 8. Results (2026-10-07, a new session with §6 in the working tree, not committed)

Claude Code 2.1.291, macOS. Claude ran each command from `Bash`, inside the sandbox.

| Case | Result | As expected? |
|---|---|---|
| S1 network | `curl --noproxy '*' https://example.com`: `Could not resolve host` (exit 6) | Yes |
| S1b network | Replaced, since no committed script opens a socket: `nc -z example.com 443` does not resolve the name, and `nc -z 1.1.1.1 443`, direct TCP to an IP, fails (exit 1) | Yes |
| S2 write | `touch` in `tests/`, `tools/`, `AGENTS.md` and `.actuarii.json`: `Operation not permitted` | Yes |
| S2b write | `touch docs/zz_probe`: works; moved to the sandbox's temporary directory | Yes |
| S3 audit trail | `touch .data/boundary_validator_audit.db`: `Operation not permitted`. `context_pack.py` still writes its log (313 → 314 lines) | Yes |
| S4 retry | `touch tests/zz_probe` with `dangerouslyDisableSandbox: true`: `Operation not permitted`; the parameter is ignored with the project's settings alone | Yes |
| S5 approval | In auto mode, `touch docs/zz_probe` asked the author for permission: the bare `Bash` rule in `ask` still applies, because `autoAllowBashIfSandboxed` is `false` | Yes |
| S6 kit | `Write` in `tests/` without a receipt: denied by the gate, naming its rule. The MCP server, outside the sandbox, still issues receipts | Yes |
| S7 suite | 2716 green and 1 failure, the same as outside the sandbox: a test pins the keys of `settings.json` and does not know `sandbox` | Yes (the failure is the change's, not the sandbox's) |
| S8 git | A branch and an empty commit work. `git checkout 5764f2f -- tools/boundary_validator/validator.py`: `unable to unlink old … Operation not permitted` | Yes, with a finding |
| S9 no sandbox | Not provoked | Declared |

**Note (2026-10-20):** ADR-022 removed the bare `"Bash"` from `ask` on 2026-10-15, the rule S5 mentions. Since then,
what asks for a `Bash` command outside the allowed list is the `default` permission mode.

**The finding of S8, not foreseen:** the `git checkout <commit> -- <path>` that failed **had already written the
index**. The file on disk was still the same as at `HEAD`, but the old version was staged, and the next `git commit`
would have stored it without going through the gate. It was undone with `git restore --staged`, which only writes in
`.git`. It is a concrete case of the path declared in §4: the index and `.git/objects` stay outside the sandbox and
the gate. The person approves the `git commit`, but the commit message does not show what is in the index.

**Another effect:** `.git/config` is protected, so the git commands that write configuration (`git branch -D` when it
cleans the branch's section, `git remote`, `git config`) warn or fail inside the sandbox. `git branch -D` deleted the
branch anyway.

**Decision, by the rule:** S1, S2, S3 and S4 come out as expected, so v0.1 relies on the sandbox for the network, the
processes and the writes through `Bash`, and the shell heuristics are declared. `allowUnsandboxedCommands: false` is
enough in the project's settings (S4); the reinforcement in the user's settings is still advisable, because of the
local file (§5).

## 9. Decisions of the author (2026-10-07)

* **`git switch`, `git merge` and the other commands that write governed paths:** the person runs them with `!`,
  outside the sandbox. No `excludedCommands`. Merging is the moment a person should look.
* **Commit integrity, in v0.1:** a git `pre-commit` hook checks that every governed path in the index matches the file
  on disk (blob and mode). With the sandbox, the disk of a governed path is written only by the gate or by the person,
  so what is committed went through one of the two. It closes the finding of S8 and the trick of `git hash-object`
  with `git update-index`.
* **The format of the commit message:** to v0.2.
* **S5:** confirmed by the author: in auto mode it asks too.
* **Commit integrity, done (2026-10-07, `9b8c29c` and `8f5eb0b`):** `tools/git/commit_integrity.py`, run by
  `tools/git/pre-commit`, installed as `.git/hooks/pre-commit`. It refuses a commit when a governed path in the index
  differs from the disk (the content, with git's filters, and the mode), and when any path in the index is spelled
  otherwise than on disk: in review, `TESTS/x.py` with false content was seen to pass next to `tests/x.py`, because
  the rule `tests/**` matches by spelling. The session announcement says whether the sandbox is on and whether the
  hook is installed. **Declared limits:** `git commit --no-verify` and git's internal commands (`commit-tree`,
  `update-ref`) skip the hooks, and `git merge` does not run the `pre-commit`; the person approves all those commands.
  With `core.fileMode` off, the check of the mode can refuse a valid commit. A name stored on disk in another Unicode
  form than in the index is refused. A governed file is committed whole.
