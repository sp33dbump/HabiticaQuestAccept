@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONUNBUFFERED=1
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "%~dp0habitica_quest_accept.py" >> "%~dp0logs\scheduled-output.log" 2>&1
) else (
  py -3 "%~dp0habitica_quest_accept.py" >> "%~dp0logs\scheduled-output.log" 2>&1
)
exit /b %ERRORLEVEL%
