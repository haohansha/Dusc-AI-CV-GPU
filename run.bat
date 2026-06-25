@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "YOLO_CONFIG_DIR=%~dp0.ultralytics"
if not exist "%YOLO_CONFIG_DIR%\Ultralytics" mkdir "%YOLO_CONFIG_DIR%\Ultralytics"
"%LOCALAPPDATA%\..\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\python.exe" -m app.demo
pause
