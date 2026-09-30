@echo off
cd /d "%~dp0"
set PYTHONUNBUFFERED=1
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "%~dp0habitica_quest_accept.py"
  goto done
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0habitica_quest_accept.py"
  goto done
)
where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0habitica_quest_accept.py"
  goto done
)
echo Python 3 was not found.
echo Install it from https://www.python.org/downloads/windows/
echo On that installer, turn on "Add python.exe to PATH".
:done
echo.
pause
