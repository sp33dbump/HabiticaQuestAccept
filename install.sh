#!/bin/bash
# Installer for Linux. Setup steps are in README.txt.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 install.py
else
  echo "Python 3 is not installed."
  echo "Debian or Ubuntu: sudo apt install python3"
  echo "Fedora: sudo dnf install python3"
  echo "Or download it from https://www.python.org/downloads/"
fi
