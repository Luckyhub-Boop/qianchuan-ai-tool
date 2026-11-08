@echo off
setlocal
title Juliang Buyin live control login
cd /d "%~dp0"
if not defined QIANCHUAN_EXTERNAL_ROOT set "QIANCHUAN_EXTERNAL_ROOT=%~dp0..\.."
for %%I in ("%QIANCHUAN_EXTERNAL_ROOT%") do set "QIANCHUAN_EXTERNAL_ROOT=%%~fI"
if not exist "data" mkdir "data"
set "NODE_EXE=%QIANCHUAN_EXTERNAL_ROOT%\runtime\node\node.exe"
if not exist "%NODE_EXE%" (
  echo [ERROR] Project runtime Node.js is missing:
  echo   %NODE_EXE%
  del "data\buyin-live-pause" >nul 2>&1
  pause
  exit /b 1
)
if not exist "%QIANCHUAN_EXTERNAL_ROOT%\node_modules\puppeteer-core\package.json" (
  echo [ERROR] Missing project dependency: %QIANCHUAN_EXTERNAL_ROOT%\node_modules\puppeteer-core
  del "data\buyin-live-pause" >nul 2>&1
  pause
  exit /b 1
)
echo A visible browser will open. Log in, select the store role,
echo then open the current live control dashboard / live big screen.
echo The browser closes automatically after verifiable live values are detected.
"%NODE_EXE%" buyin-live-agent.js --login
set "LOGIN_EXIT=%ERRORLEVEL%"
del "data\buyin-live-pause" >nul 2>&1
if not "%LOGIN_EXIT%"=="0" (
  echo [ERROR] Buyin login helper exited with code %LOGIN_EXIT%.
  echo Check data\buyin-live-agent.log for the exact page-detection error.
  pause
  exit /b %LOGIN_EXIT%
)
echo.
echo [OK] Buyin live-control URL and login session were saved.
echo Waiting for the background headless collector to take over...
timeout /t 12 /nobreak >nul
start "" "http://127.0.0.1:8765/?v=20261106-whisper-5m#review"
pause
exit /b 0
