#!/bin/bash
# Runs the LiteCraft originals guard (guard.py) with a working Python.
#
# On a new Mac without the Command Line Tools, /usr/bin/python3 is only a stub that pops up
# an install dialog. Then the guard can't run — and a failing guard blocks every tool call,
# which would stop setup from even checking the Mac. Instead, without Python, ask the user
# about anything that mentions LiteCraft, LightCraft or an external volume, and let the
# rest through to Claude Code's normal permission flow.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=""
if xcode-select -p >/dev/null 2>&1 && [[ -x /usr/bin/python3 ]]; then
  PY=/usr/bin/python3
else
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    [[ -x "$p" ]] && { PY="$p"; break; }
  done
fi

if [[ -n "$PY" ]]; then
  exec "$PY" "$DIR/guard.py"
fi

INPUT="$(cat)"
if grep -q -i -e 'litecraft' -e 'lightcraft' -e '/Volumes/' <<<"$INPUT"; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"LiteCraft originals guard: Python is not installed yet, so this can'"'"'t be checked automatically. Allow it only if it looks right."}}'
fi
exit 0
