@echo off
setlocal
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install Node.js or add it to PATH, then try again.
  pause
  exit /b 1
)

echo Starting Tuyennn Local Toolbox...
start "" "http://127.0.0.1:4173/#video"
node server.mjs

if errorlevel 1 (
  echo.
  echo The toolbox stopped with an error.
  pause
)

