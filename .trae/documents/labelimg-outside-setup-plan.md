# LabelImg 沙箱外稳定运行方案

## 一、问题

沙箱内的 Python 环境（TRAE SOLO CN 内置 Python）运行 PyQt5 GUI 会崩溃/闪退。LabelImg 需要在一个**独立的、完整的 Python 环境**中运行。

## 二、方案

创建一个 `labelimg_outside.bat` 脚本，用户从 Windows 命令提示符直接双击运行。

脚本做两件事：
1. 检测系统是否有 `labelImg`，没有则自动 `pip install`
2. 启动 LabelImg，直接指向 `data/factory_frames/` 和 `configs/predefined_classes.txt`

无需用户手动操作，一键启动。

## 三、要创建的文件

### 3.1 `labelimg_outside.bat`（项目根目录）

```batch
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
```

脚本逻辑：
- 第 4-10 行：检查系统 Python 是否可用
- 第 12-21 行：检查 labelImg 是否已安装，未安装则自动安装（使用清华镜像加速）
- 第 23-25 行：启动 LabelImg，自动加载 208 帧图片和 `smoke` 类别

## 四、用户操作

1. 确保电脑安装了 Python 3.8+ 并已加入 PATH（[python.org](https://www.python.org/) 下载安装时勾选 "Add Python to PATH"）
2. 双击 `labelimg_outside.bat` 即可启动
3. 如果尚未安装 Python，安装后再次双击脚本即可

## 五、现有数据文件（已就绪，无需改动）

| 路径 | 内容 |
|------|------|
| `data/factory_frames/` | 208 帧抽帧图片 |
| `configs/predefined_classes.txt` | 类别定义（`smoke`） |

## 六、验证

双击 `labelimg_outside.bat` → 弹出 LabelImg 窗口 → 左侧显示 YOLO 格式 → 右侧显示 208 张图片 → 可以正常画框标注
