#!/bin/sh
# SessionStart hook: puts tools/bin, the Python gate of AGENTS 2.5 (tools/bin/python3), first on the
# PATH of every Bash call of the session. It appends one line, export PATH='<tools/bin>':"$PATH",
# to $CLAUDE_ENV_FILE, which the harness sources before each Bash call; <tools/bin> is the physical
# path of the directory next to this hook, found from $0 and not from the cwd. It prints nothing and
# exits 0. Without $CLAUDE_ENV_FILE, or when the append fails, the gate is not active: it says so on
# stderr in a line starting "python gate:" (exit 0 without the variable, 1 when the append fails).

if [ -z "${CLAUDE_ENV_FILE:-}" ]; then
  echo "python gate: CLAUDE_ENV_FILE is not set; the gate is not active in this session" >&2
  exit 0
fi

here=${0%/*}
[ "$here" != "$0" ] || here=.
bin=$(cd -P -- "$here/../bin" 2>/dev/null && pwd -P) || {
  echo "python gate: tools/bin not found next to the hook; the gate is not active" >&2
  exit 1
}

quoted= rest=$bin
while :; do
  case $rest in
    *\'*) quoted=$quoted${rest%%\'*}"'\\''"; rest=${rest#*\'} ;;
    *) quoted=$quoted$rest; break ;;
  esac
done

{ printf 'export PATH=%s:"$PATH"\n' "'$quoted'" >> "$CLAUDE_ENV_FILE"; } 2>/dev/null || {
  echo "python gate: cannot append to $CLAUDE_ENV_FILE; the gate is not active" >&2
  exit 1
}
