#!/usr/bin/env python3
"""Install the daily Habitica quest-accept job on macOS or Windows.

Interactive use asks for the User ID and API Token. Those values are written
to config.json in this folder (mode 600 on macOS) and are not placed in the
scheduled task.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import schedule_setup as schedule

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
SCRIPT_PATH = ROOT / "habitica_quest_accept.py"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
API_PAGE = "https://habitica.com/user/settings/api"


def looks_like_uuid(value: str) -> bool:
    """Habitica User IDs and API Tokens are UUIDs."""
    return bool(UUID_RE.match(value.strip()))


def python_is_new_enough(executable: str) -> bool:
    """True when executable is Python 3.9 or newer."""
    try:
        out = subprocess.run(
            [executable, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    major_text, _, minor_text = out.stdout.strip().partition(".")
    try:
        return (int(major_text), int(minor_text)) >= (3, 9)
    except ValueError:
        return False


def find_python() -> str:
    """Prefer the interpreter that launched the installer when it is 3.9+."""
    if sys.version_info >= (3, 9):
        return sys.executable
    candidates = ["py", "python3", "python"] if sys.platform == "win32" else ["python3", "python"]
    for name in candidates:
        command = [name, "-3"] if name == "py" else [name]
        if python_is_new_enough(command[0] if name != "py" else name):
            # The Windows launcher needs the -3 flag to select Python 3.
            if name == "py":
                return name
            return command[0]
    return ""


def launcher_command(python_name: str) -> list[str]:
    """Argv prefix that runs Python 3 for venv creation."""
    if python_name == "py":
        return ["py", "-3"]
    return [python_name]


def ensure_venv(python_name: str) -> Path:
    """Create .venv when needed. Fall back to the system interpreter on failure."""
    target = schedule.venv_python(ROOT)
    if target.is_file():
        return target
    print("Creating a private Python environment in .venv ...")
    try:
        subprocess.run([*launcher_command(python_name), "-m", "venv", str(ROOT / ".venv")], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Could not create .venv ({exc}). The daily job will use {python_name} directly.")
        return Path(python_name)
    if target.is_file():
        return target
    print(f"Private environment is missing its Python. Using {python_name} directly.")
    return Path(python_name)


def prompt_uuid(label: str, hidden: bool) -> str:
    """Ask until the paste looks like a Habitica id. Hidden input is for the token."""
    print()
    print(label)
    print(f"Copy it from {API_PAGE}")
    while True:
        if hidden:
            print("The paste is hidden. If nothing seems to happen, paste, then press Enter.")
            value = getpass.getpass("API Token: ").strip().strip('"').strip("'")
        else:
            value = input("User ID: ").strip().strip('"').strip("'")
        if looks_like_uuid(value):
            return value
        print("That does not look like the code on the API page.")
        print("It should be 36 characters with four dashes. Copy the whole value and try again.")


def collect_credentials(args: argparse.Namespace) -> dict[str, str] | None:
    """Return credentials from flags or prompts. None means dry-run with nothing saved."""
    user_id = (args.user_id or "").strip()
    api_token = (args.api_token or "").strip()
    if args.dry_run and not user_id and not api_token:
        return None
    if not user_id or not api_token:
        if not sys.stdin.isatty():
            print("Pass --user-id and --api-token, or run the installer in a window you can type in.")
            return {}
        print("Habitica needs two codes from your account. Neither code is sent anywhere except Habitica.")
        print(f"Open {API_PAGE}")
        print("A picture of that page: https://habitica.fandom.com/wiki/API_Options")
        if not user_id:
            user_id = prompt_uuid("First, copy your User ID (it is safe to show).", hidden=False)
        if not api_token:
            api_token = prompt_uuid(
                "Next, click Show API Token on that same page and copy the token. Treat it like a password.",
                hidden=True,
            )
    if not looks_like_uuid(user_id) or not looks_like_uuid(api_token):
        print(f"User ID and API Token must both be copied from {API_PAGE}")
        return {}
    return {"user_id": user_id, "api_token": api_token}


def write_config(credentials: dict[str, str]) -> None:
    """Save credentials beside the script. Restrict the file on Unix."""
    CONFIG_PATH.write_text(json.dumps(credentials, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)


def install_macos(python_bin: Path, hour: int, minute: int, dry_run: bool) -> None:
    """Write and load a LaunchAgent for the current user."""
    logs = ROOT / "logs"
    plist = schedule.launchd_plist(
        python_bin,
        SCRIPT_PATH,
        ROOT,
        logs / "scheduled-output.log",
        logs / "scheduled-error.log",
        hour,
        minute,
    )
    destination = schedule.launchd_plist_path()
    print(f"Mac daily job: {destination}")
    print(f"Runs at {schedule.format_time(hour, minute)} local time.")
    if dry_run:
        print("Dry run: launchd file not written.")
        return
    logs.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(plist, encoding="utf-8")
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(destination)], check=True)


def install_windows(hour: int, minute: int, dry_run: bool) -> None:
    """Register a current-user daily task that runs run_daily.bat."""
    xml_text = schedule.windows_task_xml(ROOT / "run_daily.bat", ROOT, hour, minute)
    print(f"Windows daily task: {schedule.TASK_NAME}")
    print(f"Runs at {schedule.format_time(hour, minute)} local time.")
    if dry_run:
        print("Dry run: scheduled task not registered.")
        return
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    xml_path = ROOT / "logs" / "habitica-quest-accept-task.xml"
    xml_path.write_text(xml_text, encoding="utf-16")
    subprocess.run(
        ["schtasks", "/Create", "/TN", schedule.TASK_NAME, "/XML", str(xml_path), "/F"],
        check=True,
    )


def run_script(python_bin: Path, extra: list[str]) -> int:
    """Run the quest script with the interpreter the job will use."""
    completed = subprocess.run([str(python_bin), str(SCRIPT_PATH), *extra], cwd=ROOT)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    """Install config.json and the once-a-day schedule."""
    parser = argparse.ArgumentParser(description="Install the daily Habitica quest-accept job.")
    parser.add_argument("--user-id", help="Habitica User ID from the API settings page")
    parser.add_argument("--api-token", help="Habitica API Token from the API settings page")
    parser.add_argument("--time", default=schedule.DEFAULT_TIME, help="Local time HH:MM (default 08:00)")
    parser.add_argument("--dry-run", action="store_true", help="Show the plan and do not change this computer")
    parser.add_argument("--run-now", action="store_true", help="After a successful check, accept a waiting quest once")
    args = parser.parse_args(argv)

    try:
        hour, minute = schedule.parse_time(args.time)
    except ValueError as exc:
        print(exc)
        return 1

    print("Habitica Quest Accept installer")
    print(f"Folder: {ROOT}")
    python_name = find_python()
    if not python_name:
        print("Python 3.9 or newer is required.")
        print("Windows: https://www.python.org/downloads/windows/")
        print("Mac: https://www.python.org/downloads/macos/")
        return 1
    print(f"Python: {python_name}")

    credentials = collect_credentials(args)
    if credentials == {}:
        return 1

    if args.dry_run:
        print("Dry run only. config.json will not be written and no daily job will be installed.")
        if sys.platform == "win32":
            install_windows(hour, minute, dry_run=True)
        elif sys.platform == "darwin":
            install_macos(Path(python_name), hour, minute, dry_run=True)
        else:
            print("The daily job installer supports macOS and Windows.")
            return 1
        print(f"Log file after a real run: {ROOT / 'logs' / 'quest-accept.log'}")
        return 0

    assert credentials is not None
    python_bin = ensure_venv(python_name)
    write_config(credentials)
    print(f"Saved credentials in {CONFIG_PATH}")
    print("Checking the codes with Habitica before scheduling the daily run...")
    check_code = run_script(python_bin, ["--check"])
    if check_code != 0:
        print("The daily job was not installed. Fix the User ID and API Token, then run the installer again.")
        return check_code

    try:
        if sys.platform == "win32":
            install_windows(hour, minute, dry_run=False)
        elif sys.platform == "darwin":
            install_macos(python_bin, hour, minute, dry_run=False)
        else:
            print("The daily job installer supports macOS and Windows. Credentials were saved; schedule it yourself.")
            return 1
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Could not install the daily job: {exc}")
        return 1

    accept_now = args.run_now
    if sys.stdin.isatty() and not args.run_now:
        answer = input("Accept a waiting quest now as well? [Y/n] ").strip().lower()
        accept_now = answer in ("", "y", "yes")
    if accept_now:
        print("Running once now...")
        now_code = run_script(python_bin, [])
        if now_code != 0:
            print("The daily job is installed, and the one-time run reported a problem. See logs/quest-accept.log")
            return now_code

    print()
    print(f"Installed. Each day at {schedule.format_time(hour, minute)} this computer accepts a waiting party quest.")
    print("The computer should be on around that time. If it was asleep, the run usually happens after it wakes.")
    print(f"Log: {ROOT / 'logs' / 'quest-accept.log'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
