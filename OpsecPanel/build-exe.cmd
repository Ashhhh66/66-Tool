@echo off
setlocal
cd /d "%~dp0"
title 66-Tool build

python -m pip install -q -r requirements.txt pyinstaller
if errorlevel 1 (
  echo pip install failed.
  exit /b 1
)

python -m PyInstaller --noconfirm --clean 66-tool.spec
if errorlevel 1 (
  echo PyInstaller failed.
  exit /b 1
)

echo.
echo Built: "%~dp0dist\66-Tool.exe"
exit /b 0
