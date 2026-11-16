@echo off
rem Chat reply bot: double-click to start, close this window or press Ctrl+C to stop
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -X utf8 chat_bot.py %*
pause
