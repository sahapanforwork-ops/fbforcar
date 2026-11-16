@echo off
rem Run the autopilot by hand:  run_autopilot.bat daily   /   run_autopilot.bat comments   (add --dry to try without posting)
rem Set it up to run by itself:  powershell -ExecutionPolicy Bypass -File setup_autopilot.ps1
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -X utf8 autopilot.py %*
pause
