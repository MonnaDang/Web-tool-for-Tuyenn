@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" goto setup
start "Tuyennn Toolbox" ".venv\Scripts\pythonw.exe" -m desktop.main
exit /b 0

:setup
echo Preparing Tuyennn Toolbox for its first run...
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "desktop\requirements.txt"
if errorlevel 1 goto failed
start "Tuyennn Toolbox" ".venv\Scripts\pythonw.exe" -m desktop.main
exit /b 0

:failed
echo.
echo Setup could not finish. Install Python 3.11 or newer, then run this file again.
pause
exit /b 1
