# 工业烟雾AI视觉识别与管理平台 规格说明书

## Why
现有项目已具备 YOLOv8 训练、推理、微调、Jetson 部署的完整后端脚本能力，但所有操作依赖命令行手动执行，缺乏统一的图形化管理界面。需要构建一个桌面应用平台，让用户通过可视化界面完成模型管理、数据导入、微调训练、Jetson 部署等全流程操作，降低使用门槛。

## What Changes
- 新建基于 PyQt5 的桌面 GUI 应用程序
- 将现有后端脚本重构为可复用的 Python 模块（model_manager、dataset_manager、train_engine、export_engine、inference_engine）
- 提供模型导入/选择/对比界面
- 提供视频/图片素材导入与管理界面
- 提供 YOLOv8 默认模型选择与微调工作流界面
- 提供 Jetson Nano 模型编译与导出界面
- 集成训练进度可视化、推理预览、结果展示
- 建立 Git 分支管理策略与版本发布流程

## Impact
- Affected specs: 全新项目，无现有 spec 受影响
- Affected code: 新建 `app/` 目录（GUI 层）、重构 `src/` 为可复用模块、新增 `modules/` 目录
- 现有 `src/` 下的脚本将被重构但保留向后兼容的命令行入口

---

## ADDED Requirements

### Requirement: 桌面应用主框架
系统 SHALL 提供一个基于 PyQt5 的桌面应用程序，包含菜单栏、工具栏、状态栏和多标签页主界面，支持 Windows 10/11 操作系统。

#### Scenario: 启动应用程序
- **WHEN** 用户双击应用程序入口
- **THEN** 系统显示主窗口，包含"模型管理"、"数据管理"、"微调训练"、"推理检测"、"Jetson部署"五个功能标签页

#### Scenario: 环境检测
- **WHEN** 应用程序启动
- **THEN** 系统自动检测 PyTorch/CUDA 可用性，并在状态栏显示 GPU 信息（型号、显存）

---

### Requirement: 模型管理
系统 SHALL 提供模型的导入、查看、选择、对比功能。

#### Scenario: 导入用户自有模型
- **WHEN** 用户在"模型管理"页点击"导入模型"
- **THEN** 系统弹出文件选择对话框，支持选择 `.pt` 格式的 YOLO 模型文件
- **AND** 系统验证模型文件有效性（读取模型类别、结构）
- **AND** 导入成功后模型出现在模型列表中，显示模型名称、类别数、文件大小、导入时间

#### Scenario: 选择默认 YOLOv8 模型
- **WHEN** 用户在"模型管理"页点击"下载默认模型"
- **THEN** 系统列出可用的 YOLOv8 预训练模型（n/s/m/l/x 五个尺寸）
- **AND** 用户选择后自动下载对应 `yolov8*.pt` 文件
- **AND** 下载完成后添加到模型列表

#### Scenario: 模型列表展示
- **WHEN** 用户查看模型列表
- **THEN** 系统以表格形式展示所有已注册模型，列包括：模型名称、类型（预训练/微调/导入）、类别数、文件大小、创建时间、状态（就绪/不可用）

#### Scenario: 模型详情查看
- **WHEN** 用户在模型列表中双击某个模型
- **THEN** 系统弹出详情对话框，展示：模型路径、架构类型、类别列表、训练信息（如有）、mAP 指标（如有）

#### Scenario: 模型对比
- **WHEN** 用户在模型列表中选择两个模型并点击"对比"
- **THEN** 系统对同一段测试视频/图片分别用两个模型推理
- **AND** 输出对比结果：检测数、置信度分布、推理耗时

---

### Requirement: 数据管理
系统 SHALL 提供视频和图片素材的导入、浏览、标注功能。

#### Scenario: 导入视频素材
- **WHEN** 用户在"数据管理"页点击"导入视频"
- **THEN** 系统弹出文件选择对话框，支持 `.mp4`、`.avi`、`.mov` 格式
- **AND** 导入后视频出现在素材列表中，显示文件名、时长、分辨率、帧率、文件大小

#### Scenario: 导入图片素材
- **WHEN** 用户在"数据管理"页点击"导入图片"
- **THEN** 系统弹出文件选择对话框，支持 `.jpg`、`.png`、`.bmp` 格式
- **AND** 支持多选/批量导入
- **AND** 导入后图片出现在素材列表中

#### Scenario: 素材预览
- **WHEN** 用户在素材列表中点击某个素材
- **THEN** 系统在右侧预览区显示：视频的首帧预览图并可播放，或图片的完整预览

#### Scenario: 视频抽帧
- **WHEN** 用户在视频素材上右键选择"抽帧"
- **THEN** 系统弹出抽帧设置对话框：抽帧间隔、输出目录
- **AND** 执行后自动按指定间隔提取关键帧

#### Scenario: 素材删除
- **WHEN** 用户在素材列表中选中素材并点击"删除"
- **THEN** 系统弹出确认对话框，确认后从列表中移除（可选是否同时删除源文件）

---

### Requirement: 微调训练
系统 SHALL 提供基于现有模型进行微调训练的完整工作流。

#### Scenario: 创建微调任务 — 使用默认素材
- **WHEN** 用户在"微调训练"页选择"使用默认数据集"
- **THEN** 系统加载项目内置 `data/smoke_dataset/` 数据集配置
- **AND** 显示数据集概览：图片数量、类别列表、train/val 划分

#### Scenario: 创建微调任务 — 使用导入素材
- **WHEN** 用户在"微调训练"页选择"使用导入素材"并勾选已导入的素材
- **THEN** 系统引导用户进入数据准备流程：
  1. 对视频素材自动抽帧（可配置间隔）
  2. 引导用户进行图片标注（启动 LabelImg 或内置标注）
  3. 自动整合标注数据为 YOLOv8 标准格式
  4. 生成数据集配置文件

#### Scenario: 训练参数配置
- **WHEN** 用户进入训练配置界面
- **THEN** 系统显示可配置参数：基础模型（从模型列表选择）、训练轮数、批次大小、学习率、图像尺寸、优化器
- **AND** 系统根据选中模型自动推荐默认参数
- **AND** 高级选项可展开：warmup、cos_lr、patience、weight_decay 等

#### Scenario: 训练执行与监控
- **WHEN** 用户点击"开始训练"
- **THEN** 系统在后台线程启动训练
- **AND** 界面显示实时训练进度：当前轮次、loss 曲线、mAP 曲线（动态图表）
- **AND** 每轮更新训练日志到界面文本框
- **AND** 支持"暂停"/"停止"操作
- **AND** 训练完成后自动将 best.pt 注册到模型列表

#### Scenario: 训练完成通知
- **WHEN** 训练完成（正常结束或 early stopping）
- **THEN** 系统弹出通知，显示最终指标（mAP@0.5、mAP@0.5-0.95、Precision、Recall）
- **AND** 自动保存训练图表（results.png、confusion_matrix.png 等）

---

### Requirement: 推理检测
系统 SHALL 提供使用已有模型对视频/图片进行推理检测的功能。

#### Scenario: 图片推理
- **WHEN** 用户在"推理检测"页选择模型和图片素材，点击"开始检测"
- **THEN** 系统执行推理，显示带检测框的结果图片
- **AND** 控制台输出每个检测目标的类别、置信度、坐标

#### Scenario: 视频推理
- **WHEN** 用户在"推理检测"页选择模型和视频素材，点击"开始检测"
- **THEN** 系统逐帧推理，实时显示检测画面（可选是否显示窗口）
- **AND** 推理完成后输出带标注的结果视频
- **AND** 显示统计：总帧数、平均 FPS、每个类别的检测数量

#### Scenario: 实时摄像头检测
- **WHEN** 用户选择"摄像头"输入源并选择模型
- **THEN** 系统打开摄像头进行实时烟雾检测
- **AND** 界面实时显示检测画面，支持按 `Q` 键退出

---

### Requirement: Jetson Nano 部署
系统 SHALL 提供将模型编译导出为 Jetson Nano 可用格式的功能。

#### Scenario: TensorRT 引擎导出
- **WHEN** 用户在"Jetson部署"页选择一个模型并点击"导出 TensorRT"
- **THEN** 系统导出 FP16 TensorRT `.engine` 文件
- **AND** 显示导出进度和文件大小
- **AND** 导出完成后显示输出路径

#### Scenario: ONNX 模型导出
- **WHEN** 用户选择"导出 ONNX"
- **THEN** 系统导出 ONNX 格式模型文件
- **AND** 显示导出进度

#### Scenario: 部署包生成
- **WHEN** 用户在"Jetson部署"页点击"生成部署包"
- **THEN** 系统生成包含以下内容的 ZIP 包：
  - 导出的模型文件（.engine / .onnx / .pt）
  - Jetson 推理脚本（smoke_detect.py）
  - 环境配置脚本（setup_jetson.sh）
  - 依赖清单（requirements_jetson.txt）
  - 使用说明
- **AND** 用户可选择保存路径

#### Scenario: 模型优化选项
- **WHEN** 用户展开"高级导出选项"
- **THEN** 系统显示：输入分辨率、FP16/INT8 精度选择、workspace 大小
- **AND** INT8 模式下提示需要校准数据

---

### Requirement: 项目设置与配置管理
系统 SHALL 提供应用级别的设置管理。

#### Scenario: 通用设置
- **WHEN** 用户打开"设置"对话框
- **THEN** 系统显示可配置项：默认模型路径、默认数据路径、输出目录、语言、主题

#### Scenario: 配置持久化
- **WHEN** 用户修改设置并保存
- **THEN** 系统将配置写入本地 JSON 配置文件
- **AND** 下次启动时自动加载

---

## 技术架构

### 技术选型
| 组件 | 选型 | 原因 |
|------|------|------|
| GUI 框架 | PyQt5 | 成熟稳定、跨平台、丰富的控件、支持 QThread 多线程 |
| 深度学习 | PyTorch + Ultralytics YOLOv8 | 已有生态，Jetson 兼容 |
| 图表绘制 | pyqtgraph 或 matplotlib | 训练曲线实时显示 |
| 图像处理 | OpenCV | 视频/图片读写和处理 |
| 配置存储 | JSON | 简单可靠 |
| 打包分发 | PyInstaller | 生成独立 exe |

### 目录结构规划
```
Dusc AI CV GPU/
├── app/                           # ★ 新增：GUI 应用层
│   ├── __init__.py
│   ├── main.py                    # 应用入口
│   ├── main_window.py             # 主窗口框架
│   ├── ui/                        # 各功能页面
│   │   ├── model_page.py          # 模型管理页面
│   │   ├── data_page.py           # 数据管理页面
│   │   ├── train_page.py          # 微调训练页面
│   │   ├── inference_page.py      # 推理检测页面
│   │   └── deploy_page.py         # Jetson 部署页面
│   ├── widgets/                   # 可复用组件
│   │   ├── model_list.py          # 模型列表组件
│   │   ├── media_preview.py       # 媒体预览组件
│   │   ├── train_monitor.py       # 训练监控组件
│   │   ├── inference_view.py      # 推理视图组件
│   │   └── log_panel.py           # 日志面板组件
│   ├── workers/                   # 后台线程（避免阻塞 UI）
│   │   ├── train_worker.py        # 训练线程
│   │   ├── export_worker.py       # 导出线程
│   │   ├── inference_worker.py    # 推理线程
│   │   └── import_worker.py       # 导入线程
│   ├── models/                    # 应用数据模型
│   │   ├── model_info.py          # 模型元数据
│   │   ├── media_info.py          # 素材元数据
│   │   └── app_config.py          # 应用配置
│   └── resources/                 # 资源文件
│       └── icons/                 # 图标
├── modules/                       # ★ 新增：重构后的业务逻辑模块
│   ├── __init__.py
│   ├── model_manager.py           # 模型管理逻辑
│   ├── dataset_manager.py         # 数据集管理逻辑
│   ├── train_engine.py            # 训练引擎
│   ├── export_engine.py           # 模型导出引擎
│   └── inference_engine.py        # 推理引擎
├── src/                           # 保留：命令行脚本入口（兼容）
│   ├── __init__.py
│   ├── train.py                   # 改：调用 modules/train_engine.py
│   ├── detect_video.py            # 改：调用 modules/inference_engine.py
│   ├── detect_image.py            # 改：调用 modules/inference_engine.py
│   ├── ...                        # 其他脚本保持或调整
├── data/
├── models/
├── configs/
├── scripts/
├── requirements.txt               # 更新：添加 PyQt5 等 GUI 依赖
└── requirements_jetson.txt
```

---

## 版本管理策略

### Git 分支模型
采用 **Git Flow** 简化版：

```
main          ← 稳定发布版本（只接受 release 和 hotfix 合并）
  │
  ├── develop ← 开发主线（日常开发合并到此分支）
  │     │
  │     ├── feature/gui-framework      # GUI 主框架
  │     ├── feature/model-management   # 模型管理模块
  │     ├── feature/data-management    # 数据管理模块
  │     ├── feature/training-workflow  # 微调训练工作流
  │     ├── feature/inference-preview  # 推理预览
  │     └── feature/jetson-deploy      # Jetson 部署
  │
  └── hotfix/*                        # 紧急修复分支
```

### 版本号规范
采用语义化版本（SemVer 2.0）：`MAJOR.MINOR.PATCH`
- MAJOR：重大架构变更或不兼容的 API 修改
- MINOR：新功能（向后兼容）
- PATCH：Bug 修复

| 版本 | 内容 |
|------|------|
| v0.1.0 | GUI 框架 + 模型管理 |
| v0.2.0 | 数据管理 + 默认模型下载 |
| v0.3.0 | 微调训练工作流 |
| v0.4.0 | 推理检测 + 模型对比 |
| v0.5.0 | Jetson 部署 + 部署包生成 |
| v1.0.0 | 整体测试、打包 exe、发布第一个正式版 |

### Commit 规范
遵循 Conventional Commits：
- `feat:` 新功能
- `fix:` Bug 修复
- `refactor:` 代码重构
- `docs:` 文档
- `style:` 代码风格
- `test:` 测试
- `chore:` 构建/工具

示例：`feat(model): add model import from local file`

### .gitignore 范围
```
venv/
__pycache__/
*.pyc
*.pt           # 模型权重（大文件，不纳入版本管理）
*.engine
*.onnx
data/factory_frames/
data/factory_dataset/train/
data/factory_dataset/val/
runs/
videos/
*.mp4
*.avi
.DS_Store
app_config.json
dist/
build/
*.spec
```
