# 项目结构规划文档

> 本文档按 5 个管理分区对项目所有文件夹进行标号整理，便于检查与管理。
> 更新日期：2026-07-01

---

## 五大分区总览

| 分区 | 名称 | 职责 | 是否进入软件发布 |
|------|------|------|------------------|
| **1** | 视觉效果设计 | 软件外观设计稿（HTML/CSS/设计文件） | 否（设计参考） |
| **2** | 软件界面设计 | 将视觉设计转为可操作界面，连接后端 | 是（界面代码） |
| **3** | 程序后端 | 核心算法（模型微调、推理、风机控制） | 是（后端代码） |
| **4** | 辅助开发 | 不在软件内但辅助开发（数据集、文档、测试、部署脚本） | 否 |
| **5** | 通用配置 | 跨多个分区使用的配置（依赖、环境、启动脚本） | 部分 |

---

## 分区 1：视觉效果设计

**职责**：纯设计文件，定义软件的视觉风格、布局、配色、字体。不包含可执行逻辑。

| 标号 | 路径 | 用途 |
|------|------|------|
| 1.1 | `ai-detection-ui-design/` | 设计稿根目录 |
| 1.1.1 | `ai-detection-ui-design/ai-detection-ui-design.design` | 设计元数据文件 |
| 1.1.2 | `ai-detection-ui-design/colors_and_type.css` | 配色与字体规范 |
| 1.1.3 | `ai-detection-ui-design/orchestration-summary.json` | 设计编排摘要 |
| 1.1.4 | `ai-detection-ui-design/pages/` | 各页面 HTML 设计稿（data-management / inference / jetson-deploy / model-management） |
| 1.1.5 | `ai-detection-ui-design/partials/` | 公共组件设计稿（project-shell） |

---

## 分区 2：软件界面设计

**职责**：基于 PyQt5 实现可操作界面，调用后端模块，展示数据与交互。界面层不直接包含算法逻辑。

| 标号 | 路径 | 用途 |
|------|------|------|
| 2.1 | `app/` | PyQt5 应用主目录 |
| 2.1.1 | `app/main.py` | 应用入口 |
| 2.1.2 | `app/main_window.py` | 主窗口（组织各页面） |
| 2.1.3 | `app/demo.py` | UI 演示入口（白主题 28px 字号） |
| 2.2 | `app/ui/` | 各功能页面 |
| 2.2.1 | `app/ui/model_page.py` | 模型管理页 |
| 2.2.2 | `app/ui/data_page.py` | 数据管理页 |
| 2.2.3 | `app/ui/train_page.py` | 训练页 |
| 2.2.4 | `app/ui/inference_page.py` | 推理页 |
| 2.2.5 | `app/ui/deploy_page.py` | Nano 部署页 |
| 2.2.6 | `app/ui/settings_dialog.py` | 设置对话框 |
| 2.3 | `app/widgets/` | 可复用控件 |
| 2.3.1 | `app/widgets/log_panel.py` | 日志面板 |
| 2.3.2 | `app/widgets/media_preview.py` | 媒体预览 |
| 2.3.3 | `app/widgets/model_list.py` | 模型列表 |
| 2.4 | `app/models/` | 界面层数据模型（dataclass） |
| 2.4.1 | `app/models/app_config.py` | 应用配置（含 Nano 环境基线） |
| 2.4.2 | `app/models/media_info.py` | 媒体信息 |
| 2.4.3 | `app/models/model_info.py` | 模型信息 |
| 2.5 | `app/workers/` | QThread 后台线程（界面与后端桥梁） |
| 2.5.1 | `app/workers/train_worker.py` | 训练线程 |
| 2.5.2 | `app/workers/inference_worker.py` | 推理线程 |
| 2.5.3 | `app/workers/export_worker.py` | 导出线程 |
| 2.5.4 | `app/workers/import_worker.py` | 导入线程 |
| 2.6 | `app/resources/` | QSS 样式表 |
| 2.6.1 | `app/resources/light.qss` | 白色主题（28px 字号） |
| 2.6.2 | `app/resources/dark.qss` | 深色主题 |

---

## 分区 3：程序后端

**职责**：核心算法实现与软件内置模型，不依赖界面。可被界面层调用，也可独立命令行运行。

| 标号 | 路径 | 用途 |
|------|------|------|
| 3.1 | `modules/` | 核心算法模块（被 app 调用） |
| 3.1.1 | `modules/train_engine.py` | 训练引擎（模型微调） |
| 3.1.2 | `modules/inference_engine.py` | 推理引擎 |
| 3.1.3 | `modules/model_manager.py` | 模型管理 |
| 3.1.4 | `modules/dataset_manager.py` | 数据集管理 |
| 3.1.5 | `modules/export_engine.py` | TensorRT 导出引擎 |
| 3.2 | `src/` | 命令行工具/独立脚本（Windows 端） |
| 3.2.1 | `src/train.py` | GPU 训练脚本 |
| 3.2.2 | `src/train_finetune.py` | 微调脚本 |
| 3.2.3 | `src/detect_video.py` | 视频推理脚本 |
| 3.2.4 | `src/detect_image.py` | 图片推理脚本 |
| 3.2.5 | `src/webcam_demo.py` | 摄像头实时推理 |
| 3.2.6 | `src/export_tensorrt.py` | TensorRT 导出 |
| 3.2.7 | `src/prepare_dataset.py` | 数据集准备 |
| 3.2.8 | `src/extract_frames.py` | 视频抽帧 |
| 3.2.9 | `src/compare_models.py` | 模型对比 |
| 3.2.10 | `src/_compare_run.py` | 对比运行（内部） |
| 3.2.11 | `src/env_setup.py` | 环境初始化（PYTHONPATH 设置） |
| 3.3 | `models/` | 软件内置默认模型权重（运行时依赖，非测试产物） |
| 3.3.1 | `models/smoke_detection_best.pt` | 训练完成的最佳模型（软件默认模型） |

---

## 分区 4：辅助开发

**职责**：不包含在软件发布物内，但开发过程必需的资源、文档、部署脚本、测试数据。

| 标号 | 路径 | 用途 |
|------|------|------|
| 4.1 | `data/` | 数据集 |
| 4.1.1 | `data/smoke_dataset/` | Roboflow 烟雾数据集（979 张） |
| 4.1.2 | `data/factory_dataset/` | 工厂数据集 |
| 4.2 | `docs/` | 项目文档 |
| 4.2.1 | `docs/JETSON_NANO_DEPLOY.md` | Nano 部署指南 |
| 4.3 | `.trae/documents/` | 开发规划文档（fine-tune、部署、UI 改版等） |
| 4.4 | `.trae/specs/` | Spec 规格文档（nano-config-baseline / smoke-ai-platform） |
| 4.5 | `src/jetson/` | Jetson Nano 部署脚本（独立运行于 Nano） |
| 4.5.1 | `src/jetson/smoke_detect.py` | Nano 实时检测脚本（GStreamer + 弹窗 + 保存） |
| 4.6 | `scripts/` | 辅助脚本 |
| 4.6.1 | `scripts/setup_jetson.sh` | Nano 环境检测脚本（纯检测不安装） |
| 4.7 | `labelimg.bat` | LabelImg 标注工具启动（Windows） |
| 4.8 | `labelimg_outside.bat` | LabelImg 外部启动 |
| 4.9 | `runs/` | 训练/推理测试输出（gitignore，测试产物） |

---

## 分区 5：通用配置

**职责**：跨多个分区共享的配置、依赖、环境。

| 标号 | 路径 | 用途 |
|------|------|------|
| 5.1 | `configs/` | 项目配置文件 |
| 5.1.1 | `configs/model_registry.json` | 模型注册表 |
| 5.1.2 | `configs/predefined_classes.txt` | 预定义类别 |
| 5.1.3 | `configs/smoke_dataset.yaml` | 数据集配置 |
| 5.2 | `requirements.txt` | Python 依赖（核心） |
| 5.3 | `requirements-gui.txt` | Python 依赖（GUI） |
| 5.4 | `requirements_jetson.txt` | Python 依赖（Nano） |
| 5.5 | `run.bat` | Windows 启动脚本 |
| 5.6 | `venv/` | Python 虚拟环境（gitignore） |
| 5.7 | `.gitignore` | Git 忽略规则 |
| 5.8 | `PROJECT_GUIDE.md` | 项目说明文档（技术栈、训练指标） |
| 5.9 | `PROJECT_STRUCTURE.md` | 本文档（结构规划） |

---

## 完整目录树（带分区标号）

```
Dusc AI CV GPU/
│
├── [1] ai-detection-ui-design/              # 视觉效果设计
│   ├── ai-detection-ui-design.design        # 1.1.1
│   ├── colors_and_type.css                  # 1.1.2
│   ├── orchestration-summary.json           # 1.1.3
│   ├── pages/                               # 1.1.4
│   └── partials/                            # 1.1.5
│
├── [2] app/                                 # 软件界面设计
│   ├── main.py                              # 2.1.1
│   ├── main_window.py                       # 2.1.2
│   ├── demo.py                              # 2.1.3
│   ├── ui/                                  # 2.2
│   ├── widgets/                             # 2.3
│   ├── models/                              # 2.4
│   ├── workers/                             # 2.5
│   └── resources/                           # 2.6
│
├── [3] modules/                             # 程序后端（模块）
│   ├── train_engine.py                      # 3.1.1
│   ├── inference_engine.py                  # 3.1.2
│   ├── model_manager.py                     # 3.1.3
│   ├── dataset_manager.py                   # 3.1.4
│   └── export_engine.py                     # 3.1.5
│
├── [3] src/                                 # 程序后端（命令行工具）
│   ├── train.py                             # 3.2.1
│   ├── detect_video.py                      # 3.2.3
│   ├── ...                                  # 3.2.x
│   └── jetson/                              # [4.5] Nano 部署脚本（辅助开发）
│       └── smoke_detect.py                  # 4.5.1
│
├── [3] models/                              # 软件内置默认模型
│   └── smoke_detection_best.pt              # 3.3.1
│
├── [4] data/                                # 辅助开发 - 数据集
│   ├── smoke_dataset/                       # 4.1.1
│   └── factory_dataset/                     # 4.1.2
│
├── [4] docs/                                # 辅助开发 - 文档
│   └── JETSON_NANO_DEPLOY.md                # 4.2.1
│
├── [4] .trae/                               # 辅助开发 - 规划与规格
│   ├── documents/                           # 4.3
│   └── specs/                               # 4.4
│
├── [4] scripts/                             # 辅助开发 - 脚本
│   └── setup_jetson.sh                      # 4.6.1
│
├── [5] configs/                             # 通用配置
│   ├── model_registry.json                  # 5.1.1
│   ├── predefined_classes.txt               # 5.1.2
│   └── smoke_dataset.yaml                   # 5.1.3
│
├── [5] requirements.txt                     # 5.2
├── [5] requirements-gui.txt                 # 5.3
├── [5] requirements_jetson.txt              # 5.4
├── [5] run.bat                              # 5.5
├── [5] .gitignore                           # 5.7
├── [5] PROJECT_GUIDE.md                     # 5.8
├── [5] PROJECT_STRUCTURE.md                 # 5.9
├── [4] labelimg.bat                         # 4.7
├── [4] labelimg_outside.bat                 # 4.8
│
├── [5] venv/                                # 5.6 (gitignore)
└── [4] runs/                                # 4.9 (gitignore，测试产物)
```

---

## 跨分区依赖关系

```
[1] 视觉效果设计
       │ (设计稿作为参考)
       ▼
[2] 软件界面设计 ◄──── 调用 ──── [3] 程序后端
       │                              │
       │                              │ 读取
       │                              ▼
       │                          [5] 通用配置
       │
       │ (开发过程使用)
       ▼
[4] 辅助开发 (数据集/文档/部署脚本/测试)
```

**关键依赖**：
- `app/`(2) → `modules/`(3)：界面调用后端引擎
- `app/`(2) → `configs/`(5)：读取 model_registry.json
- `modules/`(3) → `configs/`(5)：读取数据集配置、模型注册表
- `modules/`(3) → `models/`(3.3)：读取内置默认模型
- `src/`(3) → `data/`(4)：训练时读取数据集
- `src/jetson/`(4) → `models/`(3.3)：部署时使用训练好的模型权重

---

## 当前现状与建议

### 现状问题
1. **`src/` 职责混合**：既有 Windows 后端脚本（3.2），又包含 Nano 部署脚本（4.5）
2. **`configs/app_config.json` 不存在**：实际只有 3 个配置文件（model_registry.json / predefined_classes.txt / smoke_dataset.yaml），之前对话提到的 app_config.json 未真正落盘。用户确认不需要重新创建，从文档中移除该条目
3. **`runs/` 为测试产物**：已归入分区 4，与 `models/`（软件内置，分区 3）区分

### 建议调整（可选，不强制）
| 建议 | 说明 |
|------|------|
| 将 `src/jetson/` 移至 `deploy/jetson/` | 与 `src/`（Windows 后端工具）分离，语义更清晰 |
| 将 `scripts/setup_jetson.sh` 移至 `deploy/jetson/` | Nano 相关脚本集中管理 |
| 将 `labelimg*.bat` 移至 `scripts/` | 工具脚本集中 |

---

## 管理检查清单

使用以下清单快速定位文件归属：

- [ ] **改 UI 外观** → 看 [1] `ai-detection-ui-design/`
- [ ] **改软件界面/交互** → 看 [2] `app/`
- [ ] **改算法/训练/推理** → 看 [3] `modules/` 或 `src/`
- [ ] **找数据集/文档/部署** → 看 [4] `data/` `docs/` `.trae/` `src/jetson/`
- [ ] **改配置/依赖/环境** → 看 [5] `configs/` `requirements*.txt` `run.bat`
