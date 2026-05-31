@echo off
chcp 65001 >nul
set "PROJECT_ROOT=%~dp0"

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Checking LabelImg installation...
python -c "import labelImg" >nul 2>&1
if %errorlevel% neq 0 (
    echo LabelImg not found, installing...
    pip install labelimg -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install LabelImg. Try: pip install labelimg
        pause
        exit /b 1
    )
)

echo Starting LabelImg...
echo Data dir: %PROJECT_ROOT%data\factory_frames\
python -c "from labelImg.labelImg import main; import sys; sys.argv = ['labelImg', r'%PROJECT_ROOT%data\factory_frames', r'%PROJECT_ROOT%configs\predefined_classes.txt', r'%PROJECT_ROOT%data\factory_frames']; main()"
