@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-cmd.ps1"
exit /b %ERRORLEVEL%
