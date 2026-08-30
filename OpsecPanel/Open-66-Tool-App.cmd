@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\pythonw.exe" (
  start "66 TOOL" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0launcher.py"
  exit /b 0
)

where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
  start "66 TOOL" pythonw "%~dp0launcher.py"
  exit /b 0
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  start "66 TOOL" python "%~dp0launcher.py"
  exit /b 0
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  start "66 TOOL" py -3 "%~dp0launcher.py"
  exit /b 0
)

echo Python was not found. Install Python and retry.
pause
exit /b 2
