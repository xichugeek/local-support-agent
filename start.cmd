@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  python -X utf8 runtime.py start
) else (
  py -3 -X utf8 runtime.py start
)
pause
