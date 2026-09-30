#!/usr/bin/env python3
"""Remove the daily Habitica quest-accept job. The Habitica account is left as it is."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import schedule_setup as schedule

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"


def remove_macos(dry_run: bool) -> None:
    """Unload and delete the LaunchAgent plist."""
    destination = schedule.launchd_plist_path()
    print(f"Mac daily job: {destination}")
    if dry_run:
        print("Dry run: launchd job not removed.")
        return
    if destination.is_file():
        domain = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False)
        destination.unlink()
        print("Removed the daily job.")
    else:
        print("No daily job file was found.")


def remove_windows(dry_run: bool) -> None:
    """Delete the Task Scheduler entry."""
    print(f"Windows daily task: {schedule.TASK_NAME}")
    if dry_run:
        print("Dry run: scheduled task not removed.")
        return
    completed = subprocess.run(
        ["schtasks", "/Delete", "/TN", schedule.TASK_NAME, "/F"],
        check=False,
    )
    if completed.returncode == 0:
        print("Removed the daily job.")
    else:
        print("No daily task was removed. It may already be gone.")


def main(argv: list[str] | None = None) -> int:
    """Remove the schedule. Optionally delete config.json."""
    parser = argparse.ArgumentParser(description="Remove the daily Habitica quest-accept job.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")
    parser.add_argument("--delete-config", action="store_true", help="Also delete config.json")
    parser.add_argument("--keep-config", action="store_true", help="Leave config.json in place")
    args = parser.parse_args(argv)

    if sys.platform == "win32":
        remove_windows(args.dry_run)
    elif sys.platform == "darwin":
        remove_macos(args.dry_run)
    else:
        print("The uninstaller supports macOS and Windows.")
        return 1

    delete_config = args.delete_config
    if sys.stdin.isatty() and not args.delete_config and not args.keep_config and not args.dry_run:
        answer = input("Delete the saved API Token in config.json? [y/N] ").strip().lower()
        delete_config = answer in ("y", "yes")
    if delete_config and not args.dry_run:
        if CONFIG_PATH.is_file():
            CONFIG_PATH.unlink()
            print(f"Deleted {CONFIG_PATH}")
        else:
            print("No config.json to delete.")
    elif args.dry_run:
        print(f"Dry run: left {CONFIG_PATH} untouched.")
    else:
        print(f"Left {CONFIG_PATH} in place.")
    print("Your Habitica account was not changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
