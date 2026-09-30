#!/usr/bin/env python3
"""Build the once-a-day Mac launchd job and Windows Task Scheduler job.

The generated job runs this folder's Python and does not contain the API token.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
LABEL = "com.habitica.quest-accept"
TASK_NAME = "HabiticaQuestAccept"
DEFAULT_TIME = "08:00"


def parse_time(value: str) -> tuple[int, int]:
    """Return hour and minute from HH:MM. Raises ValueError when it is unusable."""
    text = value.strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Use a time like 08:00")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Hour must be 0-23 and minute must be 0-59")
    return hour, minute


def format_time(hour: int, minute: int) -> str:
    """Format a clock time for display and for Task Scheduler."""
    return f"{hour:02d}:{minute:02d}"


def venv_python(root: Path = ROOT) -> Path:
    """Path of the project virtualenv interpreter for this operating system."""
    if sys.platform == "win32":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def launchd_plist_path() -> Path:
    """Where macOS expects this user's agent definition."""
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def launchd_plist(
    python_bin: Path,
    script_path: Path,
    workdir: Path,
    log_out: Path,
    log_err: Path,
    hour: int,
    minute: int,
) -> str:
    """XML for a calendar LaunchAgent. Secrets do not belong in this file."""

    def text(value: object) -> str:
        return escape(str(value))

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{text(LABEL)}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{text(python_bin)}</string>
    <string>{text(script_path)}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{text(workdir)}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{text(log_out)}</string>
  <key>StandardErrorPath</key>
  <string>{text(log_err)}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
"""


def windows_task_xml(bat_path: Path, workdir: Path, hour: int, minute: int) -> str:
    """Task Scheduler XML. StartWhenAvailable covers a missed morning boot."""
    clock = format_time(hour, minute)
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Accept a pending Habitica party quest invitation once a day.</Description>
    <URI>\\{escape(TASK_NAME)}</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{clock}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(bat_path))}</Command>
      <WorkingDirectory>{escape(str(workdir))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
