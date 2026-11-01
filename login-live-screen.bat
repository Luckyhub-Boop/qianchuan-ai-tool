@echo off
setlocal
title Qianchuan live screen login
cd /d "%~dp0"
if not exist "data" mkdir "data"
echo login> "data\live-screen-pause"
set "NODE_EXE=%~dp0runtime\node\node.exe"
if not exist "%NODE_EXE%" (
  echo [ERROR] Project runtime Node.js is missing:
  echo   %NODE_EXE%
  echo Restore the project runtime\node folder and try again.
  del "data\live-screen-pause" >nul 2>&1
  pause
  exit /b 1
)
"%NODE_EXE%" --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Project runtime Node.js cannot run:
  echo   %NODE_EXE%
  del "data\live-screen-pause" >nul 2>&1
  pause
  exit /b 1
)
if not exist "node_modules\puppeteer-core\package.json" (
  echo [ERROR] Missing project dependency: node_modules\puppeteer-core
  echo Restore node_modules or run npm install once on the project.
  del "data\live-screen-pause" >nul 2>&1
  pause
  exit /b 1
)
echo Using project runtime: %NODE_EXE%
echo Taking over the background collector and opening the live-screen login...
"%NODE_EXE%" live-screen-agent.js --login
set "LOGIN_EXIT=%ERRORLEVEL%"
del "data\live-screen-pause" >nul 2>&1
if not "%LOGIN_EXIT%"=="0" (
  echo [ERROR] Login helper exited with code %LOGIN_EXIT%.
  echo Check data\live-screen-agent.log for the exact page-detection error.
  pause
  exit /b %LOGIN_EXIT%
)
echo.
echo [OK] Live-screen address and EBP login state were saved.
echo The visible browser closes automatically only after this success is recorded.
echo This is a handoff to the background headless collector, not a crash.
echo Waiting for the background collector to take over...
timeout /t 12 /nobreak >nul
start "" "http://127.0.0.1:8765/#diagnosis"
pause
exit /b 0
