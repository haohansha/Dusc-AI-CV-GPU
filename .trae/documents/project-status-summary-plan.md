# 项目状态总结文档 & Git 提交 —— 实施方案

## 一、目标

1. 在项目根目录创建 `PROJECT_GUIDE.md`，全面说明项目当前状态、每个文件夹/文件的作用
2. 详细说明如何使用代码对视频进行烟雾浓度检测（准备文件、运行方式、输出结果类型）
3. 初始化 Git 仓库并提交当前项目文件

---

## 二、当前项目状态摘要

| 项目 | 状态 |
|------|------|
| **GPU 环境** | PyTorch 2.11.0+cu128, RTX 5060 Ti (8GB), CUDA 可用 |
| **AI 框架** | Ultralytics YOLOv8 8.4.57 |
| **模型权重** | `models/smoke_detection_best.pt`（已训练完成） |
| **训练数据** | Roboflow fire-wrpgm 数据集, 979张图片, 3类(fire/default/smoke) |
| **模型性能** | Smoke mAP@0.5 = 0.979, Overall mAP@0.5 = 0.938 |
| **推理速度** | RTX 5060 Ti 约 2.6ms/帧 (≈385 FPS) |
| **Git** | 未初始化 |

---

## 三、要创建的文件

### 3.1 `PROJECT_GUIDE.md`（项目根目录）

文档结构如下：

#### 第一部分：项目概述
- 项目名称、目标、技术栈
- 系统架构简图（摄像头 → Jetson Orin Nano → YOLOv8 → 风机控制）

#### 第二部分：目录结构说明
逐一对每个文件夹和文件进行说明：

| 路径 | 类型 | 作用 |
|------|------|------|
| `src/train.py` | 脚本 | GPU训练入口，加载yolov8n.pt预训练权重，100轮AdamW训练 |
| `src/detect_video.py` | 脚本 | 视频推理：输入视频 → YOLO检测 → 输出带标注视频 |
| `src/detect_image.py` | 脚本 | 单张图片推理 |
| `src/webcam_demo.py` | 脚本 | 摄像头实时推理演示 |
| `src/env_setup.py` | 模块 | 环境初始化（PYTHONPATH + YOLO_CONFIG_DIR） |
| `configs/smoke_dataset.yaml` | YAML | 备用数据集配置（相对路径版） |
| `data/smoke_dataset/` | 目录 | 训练/验证/测试数据（979张图，3分类） |
| `data/smoke_dataset/smoke_data.yaml` | YAML | 主数据集配置文件 |
| `models/smoke_detection_best.pt` | 权重 | 训练完成的最佳模型（Smoke mAP=0.979） |
| `runs/train/smoke_detection/` | 目录 | 训练输出：权重、指标CSV、曲线图、混淆矩阵 |
| `runs/detect/` | 目录 | 推理输出：验证结果图表、视频检测输出 |
| `venv/Lib/site-packages/` | 目录 | 本地 Python 依赖环境 |
| `requirements.txt` | 文件 | Python 依赖清单 |
| `run.bat` | 脚本 | Windows 快速启动脚本 |
| `.gitignore` | 文件 | Git 忽略规则 |

#### 第三部分：视频烟雾浓度检测使用指南

##### 3.1 需要准备的文件
1. 模型权重文件：`models/smoke_detection_best.pt`（已就绪）
2. 输入视频文件：任意格式（mp4/avi/mov等）
3. Python 环境：`venv/` 目录已包含所有依赖

##### 3.2 运行方式

**方式一：通过 run.bat 启动**
```batch
run.bat src\detect_video.py --video path\to\your_video.mp4
```
可选参数：`--conf 0.5`（提高置信度阈值）、`--show`（实时窗口显示）、`--no-save`（不保存结果）

**方式二：直接 Python 运行**（需先设置 PYTHONPATH）
```batch
set PYTHONPATH=venv\Lib\site-packages;%PYTHONPATH%
set YOLO_CONFIG_DIR=.ultralytics
python src\detect_video.py --video your_video.mp4 --conf 0.5
```

##### 3.3 运行流程说明
1. 脚本加载 `models/smoke_detection_best.pt` 模型
2. 使用 OpenCV 逐帧读取输入视频
3. 每帧送入 YOLOv8 模型进行 GPU 推理
4. 检测结果叠加到原帧上（绘制边界框 + 类别标签 + 置信度）
5. 在帧左上角叠加实时 FPS 信息
6. 所有处理后的帧编码为 MP4 视频输出
7. 控制台每 100 帧打印一次进度和平均 FPS
8. 完成后打印总帧数、平均推理时间和 FPS

##### 3.4 检测结果类型

| 输出类型 | 格式 | 保存路径 | 说明 |
|----------|------|----------|------|
| **带标注的视频** | `.mp4` | `runs/detect/video_result/output.mp4` | 每帧叠加了检测框、类别标签、置信度、FPS |
| **控制台日志** | 文本 | 终端标准输出 | 帧数进度、每帧推理时间、平均FPS |

> 注意：
> - 当前版本输出的是带标注的视频文件，不包含独立的 JSON/CSV 检测报告
> - 检测框在视频中直接可见，YOLO 以不同颜色标注不同类别（fire=橙色，smoke=红色）
> - 如需结构化检测数据（每帧检测到的类别、坐标、置信度），可在后续阶段扩展

##### 3.5 示例命令
```batch
run.bat src\detect_video.py --video data\smoke_dataset\test\images\img_361_jpg.rf.09f5e55c9fe85afea6f3558de58dfd56.jpg

假设是视频文件：
run.bat src\detect_video.py --video E:\videos\foundry_smoke.mp4 --conf 0.4 --show
```
（注：第二个命令会同时显示实时窗口 + 保存输出视频）

#### 第四部分：检测结果的烟雾浓度判定逻辑

当前模型输出的是目标检测结果（类别 + 边界框 + 置信度），烟雾浓度的判定逻辑如下：

1. **YOLO模型检测**：识别画面中 smoke 类别目标的边界框和置信度
2. **浓度推断方式**（当前阶段使用检测框信息间接推断）：
   - 检测框面积占比 → 烟雾区域越大，浓度越高
   - 检测置信度 → 模型确信度越高，烟雾可能越浓
   - 同时检测到的 smoke 框数量 → 多处烟雾表明扩散范围广
3. **后续 Phase 2 规划**：直接训练 `smoke_light/smoke_medium/smoke_heavy` 三级分类

#### 第五部分：模型训练指标

| 指标 | 值 | 说明 |
|------|-----|------|
| Smoke mAP@0.5 | 0.979 | 烟雾检测平均精度 |
| Fire mAP@0.5 | 0.898 | 火焰检测平均精度 |
| Overall mAP@0.5 | 0.938 | 综合平均精度 |
| Best Precision | 0.958 | 最佳精确率 |
| Best Recall | 0.847 | 最佳召回率 |
| 推理速度 | 2.6ms/帧 | RTX 5060 Ti GPU |
| 训练轮数 | ~90 epochs | early stopping 终止 |

---

## 四、Git 初始化与提交

### 4.1 操作步骤

```bash
cd "e:\project\Dusc AI CV GPU"
git init
git add -A
git status  # 确认 .gitignore 规则生效
git commit -m "feat: 铸造工业粉尘AI视觉识别 - 烟雾检测 Phase 1 完成
使用 YOLOv8n 训练烟雾/火焰检测模型 (Smoke mAP@0.5 = 0.979)
包含图片推理、视频推理、摄像头实时推理三种模式"
```

### 4.2 .gitignore 已配置忽略项
- `runs/` — 训练输出和推理结果（体积大，非源码）
- `models/*.pt` — 模型权重文件（体积大）
- `data/smoke_dataset/` — 数据集图片（版权原因 + 体积大）
- `venv/` — Python 虚拟环境
- `__pycache__/`, `*.pyc` — Python 缓存
- `.DS_Store`, `.env` — 系统/敏感文件

### 4.3 Git 提交后文件清单

会被 Git 跟踪的文件：
```
.gitignore
requirements.txt
run.bat
configs/smoke_dataset.yaml
src/train.py
src/detect_image.py
src/detect_video.py
src/webcam_demo.py
src/env_setup.py
PROJECT_GUIDE.md
data/smoke_dataset/smoke_data.yaml
data/smoke_dataset/README.dataset.txt
data/smoke_dataset/README.roboflow.txt
data/smoke_dataset/data.yaml
.trae/documents/foundry-smoke-ai-fan-control-plan.md
.trae/documents/project-status-summary-plan.md
```

---

## 五、验证标准

| 步骤 | 验证方法 |
|------|----------|
| 文档创建 | 确认 `PROJECT_GUIDE.md` 存在于项目根目录 |
| 文档完整性 | 包含：目录说明、使用指南、结果类型说明、模型指标 |
| Git 初始化 | `git status` 显示 "On branch main/master" |
| Git 提交 | `git log` 显示一条提交记录 |
| .gitignore 生效 | `runs/`, `models/*.pt`, `venv/`, `data/smoke_dataset/` 中的文件未被跟踪 |
