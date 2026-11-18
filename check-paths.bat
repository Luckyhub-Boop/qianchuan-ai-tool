@echo off
setlocal
set "ROOT=%~dp0"
for %%I in ("%ROOT%..\..") do set "EXT=%%~fI"
set "PY=%EXT%\runtime\python\python.exe"
if not exist "%PY%" (
  echo python runtime not found: %PY%
  echo run setup-runtime.ps1 first
  pause
  exit /b 2
)
"%PY%" -X utf8 "%ROOT%check_paths.py"
set "CODE=%ERRORLEVEL%"
pause
exit /b %CODE%
