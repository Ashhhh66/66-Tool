@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-shortcut.ps1"
if errorlevel 1 (
  echo Shortcut install failed.
  pause
  exit /b 1
)
echo.
pause
