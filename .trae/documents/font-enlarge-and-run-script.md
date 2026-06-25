# 字体放大 + 运行脚本 - 实现计划

## 概述

当前 Demo 窗口字体过小（基础字号 13px），用户要求窗口内所有字体至少 20 号。同时需要一个名为 `run` 的脚本，方便随时启动窗口进行调整。

## 当前状态分析

通过阅读源码确认字体来源：

| 字体来源 | 位置 | 当前值 | 影响范围 |
|----------|------|--------|----------|
| QSS 全局基础字号 | [dark.qss](file:///e:/project/Dusc%20AI%20CV%20GPU/app/resources/dark.qss#L2) 第2行 `QWidget { ... font-size: 13px; }` | 13px | 所有继承 QWidget 的控件（按钮/标签/输入框/表格等绝大多数控件） |
| 日志面板硬编码字体 | [demo.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/demo.py#L385) 第385行 `QFont("Courier New", 10)` | 10pt | 微调训练面板内的日志文本框 |

其他控件（QTabBar::tab、QHeaderView::section、QPushButton 等）在 QSS 中只设置了 padding，未显式设置 font-size，因此会继承 QWidget 的 13px。只要把 QWidget 基础字号提升到 20px，绝大多数控件会自动放大。

运行脚本现状：[run.bat](file:///e:/project/Dusc%20AI%20CV%20GPU/run.bat) 是一个通用 Python 包装器（透传 `%*`），直接双击不会启动任何程序，需要带参数如 `run.bat -m app.demo`。用户希望 `run` 直接打开窗口。

## 实现方案

### 改动 1：放大 QSS 基础字号

**文件**：`app/resources/dark.qss`

**修改**：第 2 行
```css
/* 修改前 */
QWidget { background-color: #2d2d2d; color: #dcdcdc; font-size: 13px; }

/* 修改后 */
QWidget { background-color: #2d2d2d; color: #dcdcdc; font-size: 20px; }
```

**效果**：所有继承 QWidget 的控件（QPushButton、QLabel、QComboBox、QTableWidget、QListWidget、QGroupBox、QSpinBox、QLineEdit、QTextEdit、QTabBar、QHeaderView、QMenuBar、QStatusBar 等）字号统一提升到 20px。

### 改动 2：放大日志面板硬编码字体

**文件**：`app/demo.py`

**修改**：第 385 行
```python
# 修改前
self.log_text.setFont(QFont("Courier New", 10))

# 修改后
self.log_text.setFont(QFont("Courier New", 20))
```

**效果**：微调训练面板的日志文本框字体从 10pt 提升到 20pt，与全局字号一致。

### 改动 3：编写运行脚本 run.bat

**文件**：`run.bat`（覆盖现有通用包装器）

**内容**：
```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "YOLO_CONFIG_DIR=%~dp0.ultralytics"
if not exist "%YOLO_CONFIG_DIR%\Ultralytics" mkdir "%YOLO_CONFIG_DIR%\Ultralytics"
"%LOCALAPPDATA%\..\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python\python.exe" -m app.demo
pause
```

**说明**：
- `chcp 65001` — 切换控制台到 UTF-8，避免中文乱码
- `cd /d "%~dp0"` — 切到脚本所在目录（项目根），确保 `python -m app.demo` 能找到模块
- 设置 `YOLO_CONFIG_DIR` 环境变量（与 main.py 一致，避免 ultralytics 配置目录警告）
- 使用 TRAE 内置 Python（已验证 torch 可正常加载）
- `pause` — 程序退出后保留窗口，方便查看错误信息
- 双击 `run.bat` 即可直接打开 Demo 窗口

## 假设与决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 字号单位 | px（20px） | 与原 QSS 单位一致；20px 在 96dpi 屏幕上约等于 15pt，视觉上显著大于原 13px |
| 是否逐控件设置字号 | 否，只改 QWidget 基础字号 | QSS 继承机制使绝大多数控件自动放大，避免逐个修改 |
| 日志字体单位 | pt（20pt） | 保持原 QFont 调用风格，20pt 等价于约 26px，确保不小于基础字号 |
| run.bat 是否覆盖 | 覆盖 | 现有 run.bat 是通用包装器，直接双击无响应；用户明确要求名为 run 的脚本直接打开窗口 |
| 是否保留通用包装能力 | 不保留 | 用户只需直接打开窗口；如需运行其他脚本可手动调用 python |

## 验证步骤

1. 双击 `run.bat`，确认 Demo 窗口正常启动
2. 肉眼确认所有 tab 页内文字字号明显增大（≥20px）
3. 切换到模型管理 tab，确认微调训练面板的日志文字也已放大
4. 关闭窗口后确认 `run.bat` 窗口显示"请按任意键继续"（pause 生效）
5. 确认无中文乱码（chcp 65001 生效）
