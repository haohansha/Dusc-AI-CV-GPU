@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "VENV_PKGS=%PROJECT_ROOT%venv\Lib\site-packages"
set "PYTHONPATH=%VENV_PKGS%;%PYTHONPATH%"
set "YOLO_CONFIG_DIR=%PROJECT_ROOT%.ultralytics"
mkdir "%YOLO_CONFIG_DIR%\Ultralytics" 2>nul
"%LOCALAPPDATA%\..\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\python.exe" %*
endlocal
