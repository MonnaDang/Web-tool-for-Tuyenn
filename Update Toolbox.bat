@echo off
setlocal
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo Git was not found. Download the newest portable release from:
  echo https://github.com/MonnaDang/Web-tool-for-Tuyenn/releases
  pause
  exit /b 1
)

git pull --ff-only origin main
if errorlevel 1 (
  echo.
  echo The update could not be applied automatically. Your files were not overwritten.
  pause
  exit /b 1
)

echo.
echo Tuyennn Toolbox is up to date. Restart the app to use the changes.
pause
