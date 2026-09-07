@echo off
rem aix launcher for Windows. All logic lives in .aix\scripts\aix.py (Python 3.9+, no dependencies).
setlocal
where py >nul 2>nul && (py -3 "%~dp0..\scripts\aix.py" %* & exit /b %errorlevel%)
where python >nul 2>nul && (python "%~dp0..\scripts\aix.py" %* & exit /b %errorlevel%)
echo aix: Python 3 not found. Install it from https://www.python.org/downloads/ 1>&2
exit /b 127
