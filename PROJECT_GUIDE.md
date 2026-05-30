# 铸造工业粉尘AI视觉识别调控风机项目

## 项目概述

基于 YOLOv8 深度学习目标检测算法，通过摄像头实时识别铸造车间（铸造炉）产生的烟雾/粉尘浓淡程度，最终实现风机频率的智能调控——烟雾淡时风机低频运行，烟雾浓时风机高频运行。

### 技术栈
| 组件 | 版本/型号 |
|------|-----------|
| AI 框架 | Ultralytics YOLOv8 8.4.57 |
| 深度学习 | PyTorch 2.11.0+cu128 |
| 训练 GPU | NVIDIA GeForce RTX 5060 Ti (8GB) |
| 边缘设备 | NVIDIA Jetson Orin Nano 8GB (待部署) |
| 编程语言 | Python 3.10.11 |
| 图像处理 | OpenCV 4.x |

### 系统架构
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  工业摄像头      │────▶│ Jetson Orin Nano  │────▶│  风机变频器      │
│  (RTSP视频流)    │     │  (YOLOv8 推理)    │     │  (频率控制)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                  │
                          ┌───────┴───────┐
                          │  训练服务器    │
                          │ (RTX 5060 Ti) │
                          └───────────────┘
```

---

## 目录结构说明

```
Dusc AI CV GPU/
│
├── .gitignore                          # Git 忽略规则（排除 runs/、venv/、模型权重、数据集图片）
├── .ultralytics/                       # Ultralytics 框架配置文件目录
├── PROJECT_GUIDE.md                    # 项目说明文档（本文件）
├── requirements.txt                    # Python 依赖清单
├── run.bat                             # Windows 快速启动脚本
├── yolov8n.pt                          # YOLOv8n 预训练权重（迁移学习起点）
│
├── configs/
│   └── smoke_dataset.yaml              # 备用数据集配置（简化版，nc=2，相对路径）
│
├── data/
│   └── smoke_dataset/                  # 烟雾/火焰数据集
│       ├── README.dataset.txt           # 数据集来源说明
│       ├── README.roboflow.txt          # Roboflow 导出说明（979张图片）
│       ├── data.yaml                    # Roboflow 原始配置
│       ├── smoke_data.yaml              # ★ 训练主配置（nc=3: fire/default/smoke）
│       ├── train/
│       │   ├── images/                  # 训练图片（~320 张）
│       │   └── labels/                  # YOLO 格式标注（每图一个 .txt）
│       ├── valid/
│       │   ├── images/                  # 验证图片（48 张）
│       │   └── labels/                  # 验证标注
│       └── test/
│           ├── images/                  # 测试图片（25 张）
│           └── labels/                  # 测试标注
│
├── models/
│   └── smoke_detection_best.pt          # ★ 训练完成的最佳模型权重
│
├── runs/                                # 训练/推理输出（Git 忽略）
│   ├── train/
│   │   └── smoke_detection/             # ★ 主训练输出
│   │       ├── weights/                  # 模型权重（best.pt、last.pt、各轮检查点）
│   │       ├── args.yaml                 # 训练超参数记录
│   │       ├── results.csv               # 每轮训练指标（loss、mAP、precision、recall）
│   │       ├── results.png               # 训练曲线图
│   │       ├── confusion_matrix.png      # 混淆矩阵
│   │       ├── F1_curve.png              # F1 曲线
│   │       ├── PR_curve.png              # Precision-Recall 曲线
│   │       └── train_batch*.jpg          # 训练批次样本可视化
│   └── detect/
│       └── video_result/                 # 视频推理输出目录
│           └── output.mp4               # 带标注的检测结果视频
│
├── src/
│   ├── env_setup.py                     # 环境初始化模块（PYTHONPATH + YOLO_CONFIG_DIR）
│   ├── train.py                         # ★ GPU 训练脚本
│   ├── detect_image.py                  # 图片推理脚本
│   ├── detect_video.py                  # ★ 视频推理脚本（主要使用）
│   └── webcam_demo.py                   # 摄像头实时推理脚本
│
└── venv/                                # Python 虚拟环境（Git 忽略）
    └── Lib/site-packages/               # PyTorch、Ultralytics、OpenCV 等依赖
```

---

## 各文件详细作用

### src/ — 核心脚本

#### train.py — GPU 训练脚本
加载 `yolov8n.pt` 预训练权重，使用 `data/smoke_dataset/smoke_data.yaml` 配置进行烟雾检测模型训练。

**关键参数：**
- epochs=100（100 轮训练，early stopping patience=20）
- imgsz=640, batch=8
- optimizer=AdamW, lr0=0.001, cos_lr=True（余弦退火）
- amp=True（自动混合精度，节省显存）
- 训练完成后自动将 best.pt 复制到 `models/smoke_detection_best.pt`

**运行：**
```batch
run.bat src\train.py
```

#### detect_video.py — 视频推理脚本（主要使用）
对视频文件逐帧进行烟雾/火焰检测，输出带标注的视频文件。

**参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--model` | `models/smoke_detection_best.pt` | 模型权重路径 |
| `--video` | 必填 | 输入视频路径 |
| `--conf` | 0.25 | 置信度阈值（0~1） |
| `--show` | False | 是否显示实时检测窗口 |
| `--no-save` | False | 不保存输出视频 |

**运行：**
```batch
run.bat src\detect_video.py --video your_video.mp4
run.bat src\detect_video.py --video your_video.mp4 --conf 0.5 --show
```

#### detect_image.py — 图片推理脚本
对单张图片进行烟雾/火焰检测，在控制台打印检测到的目标类别和置信度。

**运行：**
```batch
run.bat src\detect_image.py --image your_image.jpg
```

#### webcam_demo.py — 摄像头实时推理脚本
打开摄像头进行实时烟雾/火焰检测。置信度 > 0.5 时标注 "HIGH"（烟雾）/ "ALERT"（火焰）。按 `q` 键退出。

**运行：**
```batch
run.bat src\webcam_demo.py
run.bat src\webcam_demo.py --camera 1 --conf 0.4
```

#### env_setup.py — 环境初始化模块
设置 Python 搜索路径指向 `venv/Lib/site-packages/`，并配置 Ultralytics 全局目录。

---

### configs/ — 配置文件

#### smoke_dataset.yaml
备用数据集配置，使用相对路径指向 `../data/smoke_dataset`，定义 2 个类别（fire, smoke）。当前主要数据配置使用 `data/smoke_dataset/smoke_data.yaml`。

---

### data/smoke_dataset/ — 数据集

- **来源**：Roboflow fire-wrpgm 项目第 8 版，CC BY 4.0 协议
- **规模**：979 张图片，已预处理为 608×608 像素
- **类别**：fire（火焰）、default（默认类）、smoke（烟雾）
- **划分**：train（训练集）、valid（验证集）、test（测试集）
- **格式**：YOLOv8 格式（每张图片对应一个同名的 .txt 标注文件）

#### smoke_data.yaml
训练使用的主配置文件，指定数据集路径和类别定义。

---

### models/ — 模型权重

#### smoke_detection_best.pt
训练完成的最佳模型权重，是所有推理脚本的默认模型。

---

### runs/ — 运行时输出

#### runs/train/smoke_detection/
训练过程的完整输出：

| 文件 | 说明 |
|------|------|
| `weights/best.pt` | 最佳模型权重 |
| `weights/last.pt` | 最后一轮权重 |
| `results.csv` | 每轮指标（loss/mAP/precision/recall） |
| `results.png` | 训练曲线图 |
| `confusion_matrix.png` | 混淆矩阵 |
| `F1_curve.png` / `PR_curve.png` | F1 和 PR 曲线 |
| `train_batch*.jpg` | 训练样本可视化 |

#### runs/detect/video_result/
视频推理输出：

| 文件 | 说明 |
|------|------|
| `output.mp4` | 带标注的检测结果视频 |

---

## 视频烟雾浓度检测使用指南

### 需要准备的文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `models/smoke_detection_best.pt` | ✅ 已就绪 | 训练好的模型权重 |
| 输入视频 | ⚠️ 需准备 | 待检测的铸造车间烟雾视频（支持 mp4/avi/mov 等格式） |
| Python 环境 | ✅ 已就绪 | `venv/` 目录已安装所有依赖 |

### 运行方式

**方法一：run.bat 启动（推荐）**

```batch
run.bat src\detect_video.py --video E:\videos\foundry_smoke.mp4
```

带参数示例：
```batch
run.bat src\detect_video.py --video E:\videos\foundry_smoke.mp4 --conf 0.4 --show
```

**方法二：手动设置环境变量后运行**

```batch
set PYTHONPATH=venv\Lib\site-packages;%PYTHONPATH%
set YOLO_CONFIG_DIR=.ultralytics
python src\detect_video.py --video your_video.mp4 --conf 0.5
```

### 运行流程

```
输入视频文件 (.mp4)
       │
       ▼
┌─────────────────────┐
│ 1. 加载模型权重      │  models/smoke_detection_best.pt
│ 2. 打开视频文件      │  OpenCV VideoCapture
│ 3. 逐帧读取          │
│ 4. GPU 推理 (YOLOv8) │  每帧约 2.6ms (RTX 5060 Ti)
│ 5. 绘制检测结果      │  边界框 + 类别标签 + 置信度 + FPS
│ 6. 写入输出视频      │  MP4 编码
└─────────────────────┘
       │
       ▼
输出结果
├── runs/detect/video_result/output.mp4  ← 带标注的视频
└── 控制台日志                              ← 帧数、FPS、推理时间
```

### 检测结果类型

| 输出类型 | 格式 | 保存路径 | 内容 |
|----------|------|----------|------|
| **带标注的视频** | `.mp4` | `runs/detect/video_result/output.mp4` | 每帧叠加检测框、类别标签、置信度、实时FPS |
| **控制台日志** | 终端文本 | 标准输出 | 视频信息、每100帧进度、总帧数和平均FPS |

> **注意**：当前版本检测结果以可视化视频为主，不包含独立的 JSON/CSV 结构化检测报告。YOLO 以不同颜色标注不同类别。如需每帧的结构化数据（类别、坐标、置信度），可以在代码中扩展输出逻辑。

### 烟雾浓度判定逻辑

当前模型通过 YOLOv8 目标检测识别 smoke 类别，浓度可以通过以下方式间接推断：

| 指标 | 含义 |
|------|------|
| 检测框面积占比 | 烟雾区域占画面比例越大 → 浓度越高 |
| 置信度 | 模型对检测结果的确信度越高 → 烟雾越明显/浓 |
| smoke 框数量 | 多处烟雾目标 → 扩散范围广 |

在后续 Phase 2 中，将直接训练 `smoke_light`（淡）、`smoke_medium`（中）、`smoke_heavy`（浓）三级分类，实现精确浓度判定。

---

## 模型训练指标

### 测试集评估结果

| 类别 | mAP@0.5 | mAP@0.5-0.95 | Precision | Recall |
|------|---------|--------------|-----------|--------|
| **smoke** | **0.979** | 0.625 | 0.837 | 0.955 |
| fire | 0.898 | 0.460 | 0.929 | 0.748 |
| **Overall** | **0.938** | 0.542 | 0.883 | 0.851 |

### 训练配置

| 参数 | 值 |
|------|-----|
| 模型 | YOLOv8n (3M 参数, 8.1 GFLOPs) |
| 训练轮数 | ~90 epochs (early stopping) |
| 优化器 | AdamW, lr=0.001, cos_lr |
| 推理速度 | 2.6ms/帧 (RTX 5060 Ti) ≈ 385 FPS |
| 显存占用 | ~1.4 GB / 8 GB |

---

## 环境搭建（从零开始）

### 前提条件
- NVIDIA GPU (RTX 30/40/50 系列) + 最新驱动
- Python 3.10+
- Git

### 安装步骤

```batch
cd "e:\project\Dusc AI CV GPU"

pip install torch==2.11.0+cu128 torchvision==0.26.0+cu128 ^
    --index-url https://download.pytorch.org/whl/cu128

pip install ultralytics opencv-python matplotlib seaborn pandas tqdm
```

> **注意**：RTX 5060 Ti 是 Blackwell 架构 (sm_120)，需要 PyTorch 2.11+cu128 或更高版本才能正确使用 GPU。

---

## 项目阶段规划

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 1** | 环境搭建 + 公开数据集训练 + 基线模型 | ✅ 已完成 |
| **Phase 2** | 铸造车间数据采集 + 三级浓度分类训练 | 🔜 待实施 |
| **Phase 3** | Jetson Orin Nano 边缘部署 + TensorRT 优化 | 🔜 待实施 |
| **Phase 4** | 风机变频器联动 + 系统集成 | 🔜 待实施 |

完整开发方案见 [项目开发方案文档](.trae/documents/foundry-smoke-ai-fan-control-plan.md)。
