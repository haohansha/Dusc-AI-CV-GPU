# 烟雾检测模型微调 — 完整实施方案

## 一、概述

### 1.1 目标
使用 2 段已准备的工厂烟雾视频，通过规范化的标注流程，对现有的 YOLOv8 烟雾检测模型进行微调（Fine-tuning），提升模型在铸造车间场景下的烟雾检测准确率。

### 1.2 需求确认

| 决策项 | 选择 |
|--------|------|
| 标注策略 | **只标注 smoke**（单类别，通过检测框特征间接判断浓度） |
| 标注工具 | **LabelImg**（本地离线工具，跨平台，直接导出 YOLO 格式） |
| 训练范围 | **混合数据集训练**（工厂标注数据 + 原有公开数据集，防止灾难性遗忘） |

### 1.3 当前环境（已确认）

| 项目 | 状态 |
|------|------|
| 训练 GPU | RTX 5060 Ti (8GB), CUDA 可用 |
| PyTorch | 2.11.0+cu128 |
| 现有模型 | `models/smoke_detection_best.pt`（YOLOv8n, Smoke mAP=0.979） |
| 工厂视频 | `videos/VID_20230423_144822.mp4` + `videos/VID_20230425_143039.mp4` |
| Python 环境 | `venv/Lib/site-packages/` 已就绪 |

---

## 二、完整流程概览

```
┌──────────────────────────────────────────────────────────────┐
│                   微调完整流程（5步）                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: 视频抽帧                                             │
│  ├── 新建脚本: src/extract_frames.py                          │
│  ├── 从2段视频按间隔提取关键帧                                  │
│  └── 输出: data/factory_frames/ 图片目录                      │
│                                                              │
│  Step 2: LabelImg 标注                                        │
│  ├── 安装 LabelImg (pip install labelImg)                    │
│  ├── 按照标注规范逐帧标注 smoke 类别                           │
│  └── 输出: 与图片同名的 .txt 标注文件 (YOLO格式)               │
│                                                              │
│  Step 3: 数据集整合                                            │
│  ├── 将标注数据合并到 YOLOv8 标准目录结构                       │
│  ├── 与原有公开数据集混合（train/valid拆分）                   │
│  └── 配置: data/factory_smoke_data.yaml                      │
│                                                              │
│  Step 4: 微调训练                                             │
│  ├── 基于 best.pt 继续训练 (transfer learning)               │
│  ├── 使用较低学习率 (lr0=0.0001)                              │
│  ├── 50 epochs, early stopping                               │
│  └── 输出: models/factory_smoke_finetuned.pt                 │
│                                                              │
│  Step 5: 对比评估                                             │
│  ├── 新脚本: src/compare_models.py                            │
│  ├── 对同一段视频用新旧模型分别推理                             │
│  └── 输出: 对比日志 + 并排检测统计                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、Step 1: 视频抽帧

### 3.1 新建脚本: `src/extract_frames.py`

| 文件 | 路径 | 作用 |
|------|------|------|
| extract_frames.py | `src/extract_frames.py` | 从视频按间隔提取关键帧，保存到 `data/factory_frames/` |

脚本核心逻辑：
```python
# 每 N 帧保存一帧图片
# 默认 N=30（约每秒1帧，对29.9fps视频）
# 可选参数: --interval 30, --output data/factory_frames
# 文件名格式: VID_20230423_144822_frame_000660.jpg (含原始帧号)
```

### 3.2 执行

```batch
run.bat src\extract_frames.py --video videos\VID_20230423_144822.mp4 --interval 15
run.bat src\extract_frames.py --video videos\VID_20230425_143039.mp4 --interval 15
```

输出目录结构：
```
data/factory_frames/
├── VID_20230423_144822_frame_000000.jpg
├── VID_20230423_144822_frame_000015.jpg
├── ...
├── VID_20230425_143039_frame_000000.jpg
└── ...
```

---

## 四、Step 2: LabelImg 标注规范

### 4.1 安装

```batch
pip install labelImg
```

在任意电脑上安装后运行：
```batch
labelImg
```

### 4.2 标注规范（标准化流程）

#### 4.2.1 启动配置

| 设置项 | 值 | 路径 |
|--------|-----|------|
| 打开目录 | `data/factory_frames/` | 图片所在目录 |
| 保存目录 | `data/factory_frames/` | 标注文件保存到同一目录 |
| 标注格式 | **YOLO** | 左侧工具栏切换 |

#### 4.2.2 标注规则

| 规则 | 说明 |
|------|------|
| **只标注 smoke** | 类别名固定为 `smoke`，class_id = 0 |
| **矩形框尽量紧密** | 只框选肉眼可见的烟雾区域，不要包含过多背景 |
| **多段烟雾分开标注** | 画面中不相连的烟雾要分别画框 |
| **稀疏/淡烟雾也要标** | 即使是边缘淡雾，只要肉眼可见就标注 |
| **不标完全透明的区域** | 完全不遮挡背景的极淡区域不标注 |
| **避免框太大** | 不要用一个超大框覆盖整个画面，精准框选烟雾主体 |

#### 4.2.3 标注工作流

1. 打开 LabelImg，点击 "Open Dir" 选择 `data/factory_frames/`
2. 点击 "Change Save Dir" 选择同一目录
3. 在左侧栏确保选中 **YOLO** 格式
4. 按 `W` 键开始画框，框选烟雾区域
5. 在弹出的类别列表中选择 `smoke`
6. 按 `Ctrl+S` 保存当前帧标注
7. 按 `D` 键跳到下一张图片
8. 重复 4-7 直到所有图片标注完成

#### 4.2.4 跨电脑可移植性

LabelImg 是标准 Python 包，通过 `pip install labelImg` 即可在任意电脑安装。标注文件是纯文本 `.txt`，可跨平台使用。

**保存标注环境的方法：**
- 在项目 `configs/` 下创建 `predefined_classes.txt` 文件，内容为 `smoke`
- LabelImg 启动时可加载此文件统一类别名：
  ```batch
  labelImg data\factory_frames\ predefined_classes.txt data\factory_frames\
  ```

### 4.3 标注文件格式

每个图片对应一个同名 `.txt` 文件：

```
# 例: VID_20230423_144822_frame_000660.txt
0 0.5234 0.4123 0.2314 0.4567
0 0.7234 0.3123 0.1214 0.3567
```

> 每行一个目标: `class_id x_center y_center width height`（全部归一化到 0~1）

---

## 五、Step 3: 数据集整合

### 5.1 目录结构

```
data/factory_dataset/
├── data.yaml                           # ★ 数据集配置
├── train/
│   ├── images/                         # 标注帧图片 + 原数据集部分图片
│   └── labels/                         # 标注文件 + 原数据集部分标注
└── val/
    ├── images/                         # 保留部分原数据集验证图片
    └── labels/
```

### 5.2 数据集拆分

| 数据来源 | 用途 | 比例 |
|----------|------|------|
| 工厂视频标注帧 | train 集 (~80%) + val 集 (~20%) | 全部 |
| 原有公开数据集 | 与工厂数据混合放入 train | 全部放入 train |

策略：将工厂标注帧按 8:2 拆分为 train/val，原有公开数据集全部放入 train 以保持泛化能力。

### 5.3 数据集配置: `data/factory_dataset/data.yaml`

```yaml
path: E:/project/Dusc AI CV GPU/data/factory_dataset
train: train/images
val: val/images

nc: 1
names:
  0: smoke
```

> **注意**：微调采用单类别 smoke（nc=1），简化模型输出聚焦烟雾检测。

### 5.4 整合脚本: `src/prepare_dataset.py`

| 文件 | 路径 | 作用 |
|------|------|------|
| prepare_dataset.py | `src/prepare_dataset.py` | 自动化整合工厂标注帧 + 原数据集，生成 `data/factory_dataset/` |

脚本功能：
1. 读取 `data/factory_frames/` 中的标注文件
2. 将工厂标注帧按 8:2 随机拆分为 train/val
3. 将原有数据集 `data/smoke_dataset/train/` 中的 smoke 标注转换为 nc=1 格式，加入 train
4. 生成 `data/factory_dataset/data.yaml`
5. 打印数据集统计信息

---

## 六、Step 4: 微调训练

### 6.1 新建脚本: `src/train_finetune.py`

| 文件 | 路径 | 作用 |
|------|------|------|
| train_finetune.py | `src/train_finetune.py` | 基于 best.pt 进行微调训练 |

### 6.2 训练参数

```python
model = YOLO("models/smoke_detection_best.pt")  # ★ 基于现有模型继续训练

model.train(
    data="data/factory_dataset/data.yaml",
    epochs=50,          # 微调不需要太多轮
    imgsz=640,
    batch=8,
    device=0,
    workers=4,
    optimizer="AdamW",
    lr0=0.0001,         # ★ 微调用低学习率（原训练 lr0=0.001）
    lrf=0.01,
    cos_lr=True,
    warmup_epochs=2,    # ★ 更短的预热
    amp=True,
    patience=15,        # ★ 更早触发 early stopping
    save=True,
    save_period=5,
    val=True,
    plots=True,
    project="runs/train",
    name="factory_finetune",
    exist_ok=True,
)
```

### 6.3 与原训练的参数对比

| 参数 | 原训练 | 微调 | 原因 |
|------|--------|------|------|
| model | yolov8n.pt | smoke_detection_best.pt | 从已有知识出发 |
| epochs | 100 | 50 | 微调收敛更快 |
| lr0 | 0.001 | 0.0001 | 小学习率防过拟合 |
| warmup_epochs | 3 | 2 | 已有较好初始权重 |
| patience | 20 | 15 | 更快触发停止 |
| data | smoke_data.yaml | factory_dataset/data.yaml | nc=3→nc=1 |

### 6.4 执行

```batch
run.bat src\train_finetune.py
```

训练完成后，最佳权重自动复制到 `models/factory_smoke_finetuned.pt`。

---

## 七、Step 5: 对比评估

### 7.1 新建脚本: `src/compare_models.py`

| 文件 | 路径 | 作用 |
|------|------|------|
| compare_models.py | `src/compare_models.py` | 用新旧模型对同一视频做推理，输出对比统计 |

### 7.2 脚本逻辑

```python
# 输入: --video videos/VID_20230423_144822.mp4
# 加载: models/smoke_detection_best.pt (旧模型)
# 加载: models/factory_smoke_finetuned.pt (新模型)
# 每10帧分别用两个模型推理一次
# 收集统计: 总检测数、平均置信度、检测帧占比
# 输出: 控制台对比表格
```

### 7.3 执行

```batch
run.bat src\compare_models.py --video videos\VID_20230423_144822.mp4
```

### 7.4 预期输出格式

```
============================================================
          烟雾检测模型微调前后对比
============================================================
视频: VID_20230423_144822.mp4 | 采样帧数: 160 (每10帧)

指标                        旧模型          新模型        变化
------------------------------------------------------------
检测到烟雾的帧数             12              ??             +??
检测到烟雾的帧占比           7.5%             ??%           +??
总检测目标数                 54              ??             +??
平均置信度                   0.42            ?.??          +?.??
平均检测框面积占比           3.2%             ?.?%         +?.?%
------------------------------------------------------------
```

---

## 八、要创建/修改的文件清单

### 8.1 新建文件

| 文件 | 作用 |
|------|------|
| `src/extract_frames.py` | 视频按间隔抽帧 |
| `src/prepare_dataset.py` | 整合标注数据 + 原数据集 |
| `src/train_finetune.py` | 微调训练脚本 |
| `src/compare_models.py` | 新旧模型对比评估 |
| `configs/predefined_classes.txt` | LabelImg 类别定义文件（`smoke`） |

### 8.2 修改文件

| 文件 | 改动 |
|------|------|
| `.gitignore` | 添加 `videos/`、`data/factory_frames/`、`data/factory_dataset/train/`、`data/factory_dataset/val/` |
| `requirements.txt` | 添加 `labelImg` |

### 8.3 不修改的文件

| 文件 | 原因 |
|------|------|
| `src/train.py` | 保留原始训练流程，微调使用独立脚本 |
| `src/detect_video.py` | 推理逻辑不变，旧模型仍可正常使用 |
| `models/smoke_detection_best.pt` | 保留旧模型用于对比 |
| `data/smoke_dataset/` | 保留原始数据集不变 |

---

## 九、标注任务量估算

| 视频 | 时长 | 帧率 | 抽样间隔 | 需标注帧数 |
|------|------|------|----------|-----------|
| VID_20230423_144822 | ~54秒 | 29.9fps | 15帧 | **~107 帧** |
| VID_20230425_143039 | 待检测 | 待检测 | 15帧 | 待检测 |
| **总计** | — | — | — | **约 200-250 帧** |

> 每帧标注约 15-30 秒，预计标注总工作量：**1-2 小时**。

---

## 十、验证标准

| 步骤 | 验证方法 |
|------|----------|
| 视频抽帧 | `data/factory_frames/` 包含抽取的 .jpg 图片 |
| LabelImg 安装 | 命令行输入 `labelImg` 可启动标注工具 |
| 标注完成 | 每张图片存在同名 .txt 文件，内容格式正确 |
| 数据集整合 | `data/factory_dataset/` 目录结构符合 YOLOv8 标准 |
| 微调训练 | 终端无报错，能正常完成 epochs + 保存 best.pt |
| 对比评估 | `compare_models.py` 输出新旧模型对比表格 |
| 效果提升 | 新模型在工厂视频上的检测帧数/置信度 ≥ 旧模型 |

---

## 十一、立即执行步骤

1. 创建 `src/extract_frames.py` 并运行抽帧
2. 安装 `labelImg` 并配置类别文件
3. （用户手动完成标注）
4. 创建 `src/prepare_dataset.py` 并运行数据整合
5. 创建 `src/train_finetune.py` 并运行微调
6. 创建 `src/compare_models.py` 并运行对比
7. 更新 `.gitignore` 和 `requirements.txt`
8. Git 提交
