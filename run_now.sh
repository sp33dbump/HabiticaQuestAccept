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
  echo "Debian or Ubuntu: sudo apt install python3"
  echo "Fedora: sudo dnf install python3"
  PY=""
fi
if [[ -n "$PY" ]]; then
  "$PY" habitica_quest_accept.py
fi
