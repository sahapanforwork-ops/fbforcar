@echo off
rem Double-click to log in to Facebook again; saves cookies for both bots (this PC only).
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -X utf8 login.py
pause
