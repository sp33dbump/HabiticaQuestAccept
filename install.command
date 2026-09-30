#!/bin/bash
# Double-click installer for macOS. Setup steps are in README.txt.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 install.py
else
  echo "Python 3 is not installed."
  echo "Download it from https://www.python.org/downloads/macos/"
  echo "Then double-click install.command again."
fi
echo
read -r -p "Press Enter to close this window..." _
