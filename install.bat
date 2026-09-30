@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 install.py
  goto done
)
where python >nul 2>&1
if %errorlevel%==0 (
  python install.py
  goto done
)
echo Python 3 was not found.
echo Install it from https://www.python.org/downloads/windows/
echo On that installer, turn on "Add python.exe to PATH".
:done
echo.
pause
