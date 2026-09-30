#!/bin/bash
# Run one quest-accept check immediately and show the result.
cd "$(dirname "$0")" || exit 1
export PYTHONUNBUFFERED=1
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "Python 3 is not installed."
  echo "Download it from https://www.python.org/downloads/macos/"
  PY=""
fi
if [[ -n "$PY" ]]; then
  "$PY" habitica_quest_accept.py
fi
echo
read -r -p "Press Enter to close this window..." _
