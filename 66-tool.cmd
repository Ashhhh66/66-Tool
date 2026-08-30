@echo off
setlocal
set "ROOT=%~dp0"
if defined PYTHONPATH (
  set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%ROOT%"
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python "%ROOT%66-tool.py" %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 "%ROOT%66-tool.py" %*
  exit /b %ERRORLEVEL%
)

echo error: Python 3 was not found. Install Python and retry. 1>&2
exit /b 2
