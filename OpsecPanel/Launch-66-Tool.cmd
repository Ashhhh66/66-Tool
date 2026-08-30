@echo off
setlocal
title 66 TOOL
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %*
  goto :done
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python "%~dp0main.py" %*
  goto :done
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 "%~dp0main.py" %*
  goto :done
)

echo Python 3 was not found. Install Python from python.org and tick "Add to PATH".
pause
exit /b 2

:done
if errorlevel 1 (
  echo.
  echo 66-Tool exited with an error.
  pause
)
exit /b %ERRORLEVEL%
