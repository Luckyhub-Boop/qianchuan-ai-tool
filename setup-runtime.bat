@echo off
chcp 65001 >nul
title 直播投放工具 - 运行环境安装
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-runtime.ps1" %*
echo.
pause
