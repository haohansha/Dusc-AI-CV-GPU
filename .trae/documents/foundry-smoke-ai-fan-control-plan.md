# 铸造工业粉尘AI视觉识别调控风机项目 — 开发方案

## 一、项目概述

### 1.1 项目目标
开发一套基于AI视觉的铸造车间烟雾粉尘检测系统，通过摄像头+边缘计算设备实时识别铸造炉产生的烟雾浓淡程度，最终实现风机频率的智能调控（烟雾淡→低频，烟雾浓→高频）。

### 1.2 系统架构总览
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

### 1.3 职责范围
- **本阶段负责**：摄像头选型 + AI模型训练 + 边缘推理部署（Jetson Orin Nano）
- **暂不涉及**：风机变频器控制接口（Modbus/模拟信号等留到后续阶段）

### 1.4 开发环境
| 项目 | 详情 |
|------|------|
| 训练机器 | Windows PC，RTX 5060 Ti 8GB VRAM，CUDA 13.2 |
| Python | 3.10.11 |
| 边缘设备 | NVIDIA Jetson Orin Nano 8GB（后续部署） |
| AI框架 | Ultralytics YOLOv8 + PyTorch |

---

## 二、需求确认

| 需求项 | 确认结果 |
|--------|----------|
| 烟雾分级 | 三级分类：smoke_light（淡）、smoke_medium（中）、smoke_heavy（浓） |
| 数据集 | 暂无铸造车间数据，第一步使用公开烟雾数据集验证 |
| YOLO版本 | YOLOv8（社区成熟，Jetson部署经验丰富） |
| 实时性 | ≥15 FPS（Jetson Orin Nano推理） |
| 风机控制 | 暂不涉及，只做AI识别部分 |

---

## 三、分阶段实施计划

### Phase 1：环境搭建 + YOLOv8烟雾检测基线（当前第一步）

**目标**：在当前PC上搭建YOLOv8 GPU训练环境，使用公开烟雾数据集训练一个可用的烟雾检测模型，验证技术路线可行。

#### 3.1 环境准备
1. 安装CUDA-compatible PyTorch（支持RTX 5060 Ti）
2. 克隆 ultralytics/ultralytics 仓库
3. 安装依赖（opencv-python, torch, torchvision 等）

#### 3.2 数据集准备
- 使用公开烟雾/火焰数据集（如 D-Fire dataset、Roboflow smoke datasets）
- 将数据集转换为YOLOv8格式
- 先做二分类（smoke / no smoke）跑通流程
- 同时规划三级分类的数据标注方案

#### 3.3 模型训练
- 使用 YOLOv8n.pt 作为预训练权重
- 在RTX 5060 Ti上进行GPU训练
- 评估 mAP、精确率、召回率

#### 3.4 推理验证
- 图片推理测试
- 视频/摄像头实时推理演示
- 性能基准测试（FPS、延迟）

#### 3.5 交付物
- 可用的 smoke detection 模型权重文件
- train.py 训练脚本
- detect.py / webcam_demo.py 推理脚本
- 训练日志和评估指标

---

### Phase 2：铸造车间数据采集与三级分类训练

**目标**：采集铸造车间烟雾粉尘数据，按三级分类标注，训练专用的多级烟雾检测模型。

#### 关键任务
- 工业摄像头选型（推荐海康/大华工业相机，支持RTSP）
- 铸造车间现场数据采集方案
- 数据标注规范制定（smoke_light / smoke_medium / smoke_heavy 的判定标准）
- 三级分类模型训练与优化

---

### Phase 3：Jetson Orin Nano边缘部署

**目标**：将训练好的模型部署到Jetson Orin Nano，实现实时推理。

#### 关键任务
- Jetson Orin Nano系统烧录与环境配置（JetPack SDK）
- 模型导出为TensorRT格式（优化推理速度）
- 摄像头RTSP视频流接入
- 实时推理管道开发（≥15 FPS）
- 推理结果输出接口（为风机控制预留）

---

### Phase 4：系统集成与联动

**目标**：将AI识别结果与风机控制系统对接。

#### 关键任务
- 风机控制协议对接（Modbus / 模拟信号）
- 烟雾浓度→风机频率的映射策略
- 系统稳定性测试与长期运行验证

---

## 四、Phase 1 详细实施方案（当前执行）

### 4.1 项目目录结构

```
Dusc AI CV GPU/
├── data/
│   └── smoke_dataset/          # 公开烟雾数据集
│       ├── images/
│       │   ├── train/
│       │   └── val/
│       └── labels/
│           ├── train/
│           └── val/
├── models/                     # 训练好的模型权重
├── src/
│   ├── train.py               # 训练脚本
│   ├── detect_image.py        # 图片推理
│   ├── detect_video.py        # 视频推理
│   └── webcam_demo.py         # 摄像头实时推理
├── configs/
│   └── smoke_dataset.yaml     # 数据集配置
├── runs/                       # 训练输出（自动生成）
├── requirements.txt
└── .gitignore
```

### 4.2 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| AI框架 | ultralytics (YOLOv8) | 社区最活跃，API简洁，Jetson部署支持好 |
| 深度学习框架 | PyTorch 2.x (CUDA 12.x) | 与RTX 5060 Ti兼容 |
| 数据集 | D-Fire / Roboflow Smoke | 公开标注数据集，含smoke类别 |
| 图像处理 | OpenCV 4.x | 视频流/摄像头读取 |
| 模型格式 | PyTorch → ONNX → TensorRT | 适配Jetson Orin Nano推理优化 |

### 4.3 GPU训练配置

```yaml
model: yolov8n.pt          # 使用nano版本预训练权重
epochs: 100
imgsz: 640
batch: 16                  # 根据8GB显存调整
device: 0                  # GPU设备号
workers: 4
optimizer: AdamW
lr0: 0.001
```

---

## 五、关键决策与假设

1. **先二分类后三级**：公开数据集只有smoke单类别，Phase 1先训练二分类模型验证流程，三级分类在Phase 2结合铸造车间数据实现。
2. **训练与推理分离**：训练在RTX 5060 Ti PC上完成，推理部署在Jetson Orin Nano。
3. **模型选型**：使用YOLOv8n（nano）兼顾精度和速度，适合Jetson边缘推理。
4. **数据标注规范**：Phase 2需制定烟雾浓淡的量化判定标准（可参考烟雾像素占比、视觉透明度等）。
5. **TensorRT加速**：Jetson部署时必须使用TensorRT推理以获得≥15 FPS性能。

---

## 六、验证标准

| 阶段 | 验证指标 | 目标值 |
|------|----------|--------|
| Phase 1 | smoke mAP@0.5 | ≥0.85 |
| Phase 1 | 推理FPS（RTX 5060 Ti） | ≥60 FPS |
| Phase 2 | multi-class mAP@0.5 | ≥0.80 |
| Phase 3 | Jetson推理FPS（TensorRT） | ≥15 FPS |
| Phase 3 | 推理延迟（端到端） | <100ms |

---

## 七、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 公开数据集与铸造烟雾差异大 | 模型迁移效果差 | Phase 2用铸造车间数据微调 |
| Jetson推理达不到15FPS | 实时性不足 | 使用TensorRT+INT8量化，降低输入分辨率 |
| 烟雾浓淡标注主观性强 | 标注一致性差 | 制定量化标注规范，使用像素占比辅助判定 |
| CUDA/PyTorch版本兼容 | 环境搭建失败 | 使用官方推荐版本组合，记录环境配置 |

---

## 八、下一步行动

Phase 1 立即执行步骤如下：

1. 安装 PyTorch CUDA 版本
2. 安装 ultralytics 及相关依赖
3. 下载公开烟雾数据集
4. 配置 YOLOv8 数据集格式
5. 在 RTX 5060 Ti 上训练模型
6. 测试推理效果
