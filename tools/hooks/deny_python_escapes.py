"""PreToolUse hook for Bash: the ways of reaching a Python interpreter around the tools/bin shim.

AGENTS 2.5 lets Python run only as a committed script under tools/ or traianus/. The shim
tools/bin/python3, first on the PATH of every Bash call (tools/hooks/session_python_gate.sh),
decides for the names it covers: python, python3, python3.11. This hook denies (exit 2) a command
whose words reach an interpreter without going through it:

R1  an interpreter named by path (a word with '/' whose last component is python*, pypy* or
    ipython*), except tools/bin/<name>, the shim named by path, which decides for itself.
R2  an interpreter name the shim does not cover (python3.12, pypy3, ipython).
R3  `pyenv exec`.
R4  a PATH reassignment: a word PATH=... or PATH+=..., or `unset` followed by PATH.
R5  `env` followed, before the next separator, by -i, --ignore-environment, a lone -, -P, or
    -u / --unset PATH.
R6  `command -p`.

Words come from shlex (POSIX rules; ; & | ( ) < > and newline are separators; # is no comment),
and each rule is applied twice: to the words, and to the words obtained by splitting every one of
them once more on whitespace and separators, so `sh -c '/usr/bin/python3 -c ...'` is caught. A
command shlex cannot tokenize is denied as unverifiable. The body of a heredoc whose delimiter is
quoted is data, not shell: it is scanned only when a shell (sh, bash, eval, ...) appears elsewhere
in the command, which may read it. Input that is not a JSON object, or a Bash payload without a
command string, is denied: exit 1 would read as a broken hook, not as a denial.

Text-level heuristic, not a shell parser. Declared limits: eval and command substitution that
assemble an interpreter path, login shells (bash -l, zsh -l) that re-read a profile and rebuild
PATH, xcrun, quoting nested more than one level, env option clusters (-iu), a `<<'TAG'` inside
quotes that hides the lines up to a line equal to TAG, and any file at */tools/bin/<name> (R1
trusts the name of the shim). The shim itself trusts the caller's PATH for git.

Standard library only: an import failure would exit 1, which the harness reads as a broken hook
rather than a denial; annotations are postponed so a 3.9 system interpreter can import it.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

SEPARATORS = frozenset(";&|()<>\n")
INTERPRETER = re.compile(r"(python|pypy|ipython)[0-9.]*")
COVERED = frozenset({"python", "python3", "python3.11"})
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "ash", "csh", "tcsh", "fish", "eval", "source", ".", "xargs"})
ENV_RESETS = frozenset({"-i", "--ignore-environment", "-", "-uPATH", "--unset=PATH"})
QUOTED_HEREDOC = re.compile(r"(?<!<)<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\(\w+))")
SPLIT = re.compile(r"[;&|()<>\n]+|[^\s;&|()<>]+")


def words(text: str) -> list[str]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars="".join(SEPARATORS))
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def strip_heredocs(command: str) -> tuple[str, list[str]]:
    """The command without the bodies of its quoted-delimiter heredocs, and those bodies."""
    kept, bodies, position = [], [], 0
    for marker in QUOTED_HEREDOC.finditer(command):
        newline = command.find("\n", marker.end())
        if marker.start() < position or newline < 0:
            continue
        tag = next(group for group in marker.groups()[1:] if group is not None)
        indent = "\t*" if marker.group(1) else ""
        closing = re.compile(f"^{indent}{re.escape(tag)}$", re.MULTILINE).search(command, newline + 1)
        if closing:
            kept.append(command[position:newline + 1])
            bodies.append(command[newline + 1:closing.start()])
            position = closing.end()
    kept.append(command[position:])
    return "".join(kept), bodies


def until_separator(tokens: list[str], start: int) -> list[str]:
    end = start
    while end < len(tokens) and not (tokens[end] and set(tokens[end]) <= SEPARATORS):
        end += 1
    return tokens[start:end]


def env_resets_path(args: list[str]) -> bool:
    return any(
        arg in ENV_RESETS or arg.startswith("-P")
        or (arg in ("-u", "--unset") and args[at + 1:at + 2] == ["PATH"])
        for at, arg in enumerate(args)
    )


def violation(tokens: list[str]) -> str | None:
    for index, word in enumerate(tokens):
        last = word.rsplit("/", 1)[-1]
        rest = until_separator(tokens, index + 1)
        if INTERPRETER.fullmatch(last):
            shim = f"tools/bin/{last}"
            if "/" in word and word != shim and not word.endswith(f"/{shim}"):
                return f"R1 interpreter named by path: {word!r}"
            if "/" not in word and last not in COVERED:
                return f"R2 interpreter the shim does not cover: {word!r}"
        if last == "pyenv" and rest[:1] == ["exec"]:
            return f"R3 pyenv exec: {word!r}"
        if word.startswith(("PATH=", "PATH+=")) or (word == "unset" and "PATH" in rest):
            return f"R4 PATH reassigned: {word!r}"
        if last == "env" and env_resets_path(rest):
            return f"R5 env resets PATH: {word!r}"
        if last == "command" and rest[:1] == ["-p"]:
            return f"R6 command -p: {word!r}"
    return None


def check(command: str) -> str | None:
    text, bodies = strip_heredocs(command)
    first = words(text)
    if any(word.rsplit("/", 1)[-1] in SHELLS for word in first):
        for body in bodies:
            first += ["\n"] + words(body)
    second = [part for word in first for part in SPLIT.findall(word)]
    return violation(first) or violation(second)


def deny(reason: str) -> int:
    sys.stderr.write(
        f"[deny_python_escapes] {reason} (AGENTS 2.5: Python runs only as a committed script "
        "under tools/ or traianus/, through tools/bin; otherwise ask the user)\n"
    )
    return 2


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, RecursionError, OSError):
        return deny("fail-closed: stdin was not valid JSON")
    if not isinstance(payload, dict):
        return deny("fail-closed: the payload is not a JSON object")
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return deny("fail-closed: a Bash payload without a command string")
    try:
        found = check(command)
    except ValueError as exc:
        return deny(f"unverifiable: the command cannot be tokenized ({exc})")
    return deny(found) if found else 0


if __name__ == "__main__":
    sys.exit(main())
