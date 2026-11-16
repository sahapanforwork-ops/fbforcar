@echo off
rem Double-click once: sets up the autopilot in Windows Task Scheduler (daily 09:07 post, comments every 2 hours 10:23-20:23).
rem To remove: run  powershell -ExecutionPolicy Bypass -File setup_autopilot.ps1 -Remove
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_autopilot.ps1"
pause
