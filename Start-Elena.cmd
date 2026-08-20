@echo off
setlocal
set "ELENA_EXE=%~dp0.venv\Scripts\elena-desktop.exe"
if not exist "%ELENA_EXE%" (
  echo Elena is not set up yet. Run Setup-Elena.ps1 first.
  pause
  exit /b 1
)
start "Elena" /min "%ELENA_EXE%"
exit /b 0