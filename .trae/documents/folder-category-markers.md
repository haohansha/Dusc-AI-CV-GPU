# 文件夹分类标记文件方案

## 摘要

按 `PROJECT_STRUCTURE.md` 的 5 大分区，在每个目录下创建 `<分类号>_category.txt` 标记文件，文件名直接体现该文件夹所属分区编号。txt 内容记录该文件夹内**当前层级**所有文件与子目录的说明（与 PROJECT_STRUCTURE.md 一致），**不递归子目录**。

## 当前状态分析

- 项目根目录：`e:\project\Dusc AI CV GPU`
- 已有 `PROJECT_STRUCTURE.md` 定义 5 大分区与编号
- 用户决策（2026-07-01）：
  1. 标记文件命名：`<分类号>_category.txt`（如 `1_category.txt`）
  2. 内容粒度：只记当前层，不递归子目录
  3. 文件列出：全部列出（含 `__init__.py`）
  4. 内容来源：与 `PROJECT_STRUCTURE.md` 中对该文件的描述一致

## 命名规则

- **文件名格式**：`<分类号>_category.txt`
  - 一级分类：`1_category.txt`、`2_category.txt`、`5_category.txt`
  - 多级分类用下划线连接：`2_2_category.txt`（2.2）、`3_1_category.txt`（3.1）、`4_5_category.txt`（4.5）
- **编码**：UTF-8
- **内容格式**：
  ```
  # <分类号> <分类名称>
  
  ## 文件
  - <文件名> | <说明>
  
  ## 子目录
  - <目录名>/ | <说明>
  ```

## 需要创建的标记文件清单（18 个 + 1 个根级）

### 分区 1：视觉效果设计

#### 1. `ai-detection-ui-design/1_category.txt`

```
# 1 视觉效果设计

## 文件
- ai-detection-ui-design.design | 设计元数据文件
- colors_and_type.css | 配色与字体规范
- orchestration-summary.json | 设计编排摘要

## 子目录
- pages/ | 各页面 HTML 设计稿（data-management / inference / jetson-deploy / model-management）
- partials/ | 公共组件设计稿（project-shell）
```

### 分区 2：软件界面设计

#### 2. `app/2_category.txt`

```
# 2 软件界面设计

## 文件
- __init__.py | Python 包标识文件
- main.py | 应用入口
- main_window.py | 主窗口（组织各页面）
- demo.py | UI 演示入口（白主题 28px 字号）

## 子目录
- ui/ | 各功能页面
- widgets/ | 可复用控件
- models/ | 界面层数据模型（dataclass）
- workers/ | QThread 后台线程（界面与后端桥梁）
- resources/ | QSS 样式表
```

#### 3. `app/ui/2_2_category.txt`

```
# 2.2 功能页面

## 文件
- __init__.py | Python 包标识文件
- model_page.py | 模型管理页
- data_page.py | 数据管理页
- train_page.py | 训练页
- inference_page.py | 推理页
- deploy_page.py | Nano 部署页
- settings_dialog.py | 设置对话框
```

#### 4. `app/widgets/2_3_category.txt`

```
# 2.3 可复用控件

## 文件
- __init__.py | Python 包标识文件
- log_panel.py | 日志面板
- media_preview.py | 媒体预览
- model_list.py | 模型列表
```

#### 5. `app/models/2_4_category.txt`

```
# 2.4 界面层数据模型（dataclass）

## 文件
- __init__.py | Python 包标识文件
- app_config.py | 应用配置（含 Nano 环境基线）
- media_info.py | 媒体信息
- model_info.py | 模型信息
```

#### 6. `app/workers/2_5_category.txt`

```
# 2.5 QThread 后台线程（界面与后端桥梁）

## 文件
- __init__.py | Python 包标识文件
- train_worker.py | 训练线程
- inference_worker.py | 推理线程
- export_worker.py | 导出线程
- import_worker.py | 导入线程
```

#### 7. `app/resources/2_6_category.txt`

```
# 2.6 QSS 样式表

## 文件
- light.qss | 白色主题（28px 字号）
- dark.qss | 深色主题
```

### 分区 3：程序后端

#### 8. `modules/3_1_category.txt`

```
# 3.1 核心算法模块（被 app 调用）

## 文件
- __init__.py | Python 包标识文件
- train_engine.py | 训练引擎（模型微调）
- inference_engine.py | 推理引擎
- model_manager.py | 模型管理
- dataset_manager.py | 数据集管理
- export_engine.py | TensorRT 导出引擎
```

#### 9. `src/3_2_category.txt`

```
# 3.2 命令行工具/独立脚本（Windows 端）

## 文件
- train.py | GPU 训练脚本
- train_finetune.py | 微调脚本
- detect_video.py | 视频推理脚本
- detect_image.py | 图片推理脚本
- webcam_demo.py | 摄像头实时推理
- export_tensorrt.py | TensorRT 导出
- prepare_dataset.py | 数据集准备
- extract_frames.py | 视频抽帧
- compare_models.py | 模型对比
- _compare_run.py | 对比运行（内部）
- env_setup.py | 环境初始化（PYTHONPATH 设置）

## 子目录
- jetson/ | Nano 部署脚本（独立运行于 Nano，分类 4.5）
```

#### 10. `models/3_3_category.txt`

```
# 3.3 软件内置默认模型权重（运行时依赖，非测试产物）

## 文件
- smoke_detection_best.pt | 训练完成的最佳模型（软件默认模型）

## 说明
- 本目录被 .gitignore 排除，.pt 文件不纳入版本控制
- 实际文件可能不存在（需从训练输出或备份恢复）
```

### 分区 4：辅助开发

#### 11. `data/4_1_category.txt`

```
# 4.1 数据集

## 子目录
- smoke_dataset/ | Roboflow 烟雾数据集（979 张）
- factory_dataset/ | 工厂数据集

## 说明
- 数据集图片和标签文件被 .gitignore 排除
- 本标记文件仅记录顶层子目录，子目录内的数据文件不逐一列出
```

#### 12. `docs/4_2_category.txt`

```
# 4.2 项目文档

## 文件
- JETSON_NANO_DEPLOY.md | Nano 部署指南
```

#### 13. `.trae/documents/4_3_category.txt`

```
# 4.3 开发规划文档（fine-tune、部署、UI 改版等）

## 文件
- fine-tuning-smoke-model-plan.md | 烟雾模型微调方案
- finetune-execute-plan.md | 微调执行计划
- font-enlarge-and-run-script.md | 字号放大与运行脚本
- foundry-smoke-ai-fan-control-plan.md | 工厂烟雾 AI 风机控制方案
- jetson-deployment-plan.md | Jetson 部署方案
- jetson-nano-deploy-guide.md | Nano 部署指南
- labelimg-outside-setup-plan.md | LabelImg 外部安装
- project-status-summary-plan.md | 项目状态总结
- round2-finetune-plan.md | 第二轮微调方案
- ui-layout-redesign.md | UI 布局重设计
- ui-redesign-implementation.md | UI 重设计实现
- video-detection-guide-plan.md | 视频检测指南方案
- folder-category-markers.md | 文件夹分类标记文件方案（本文档所属方案）
```

#### 14. `.trae/specs/4_4_category.txt`

```
# 4.4 Spec 规格文档

## 子目录
- nano-config-baseline/ | Nano 环境参数全局化 spec
- smoke-ai-platform/ | 烟雾 AI 平台 spec
```

#### 15. `src/jetson/4_5_category.txt`

```
# 4.5 Jetson Nano 部署脚本（独立运行于 Nano）

## 文件
- smoke_detect.py | Nano 实时检测脚本（GStreamer + 弹窗 + 保存）
```

#### 16. `scripts/4_6_category.txt`

```
# 4.6 辅助脚本

## 文件
- setup_jetson.sh | Nano 环境检测脚本（纯检测不安装）
```

#### 17. `runs/4_9_category.txt`

```
# 4.9 训练/推理测试输出（gitignore，测试产物）

## 说明
- 本目录被 .gitignore 排除，所有内容为运行时产物
- 典型子目录：
  - train/ | 训练输出（权重、曲线图、混淆矩阵等）
  - detect/ | 推理输出（带标注的视频）
- 本标记文件仅记录说明，不列出具体文件（运行时动态生成）
```

### 分区 5：通用配置

#### 18. `configs/5_1_category.txt`

```
# 5.1 项目配置文件

## 文件
- model_registry.json | 模型注册表
- predefined_classes.txt | 预定义类别
- smoke_dataset.yaml | 数据集配置
```

### 根目录散落文件

#### 19. `0_root_category.txt`（根目录标记文件）

```
# 0 项目根目录

## 说明
本文件记录项目根目录下散落文件的分类归属，便于管理。

## 分区 4 - 辅助开发
- labelimg.bat | LabelImg 标注工具启动（Windows）- 4.7
- labelimg_outside.bat | LabelImg 外部启动 - 4.8

## 分区 5 - 通用配置
- requirements.txt | Python 依赖（核心）- 5.2
- requirements-gui.txt | Python 依赖（GUI）- 5.3
- requirements_jetson.txt | Python 依赖（Nano）- 5.4
- run.bat | Windows 启动脚本 - 5.5
- .gitignore | Git 忽略规则 - 5.7
- PROJECT_GUIDE.md | 项目说明文档（技术栈、训练指标）- 5.8
- PROJECT_STRUCTURE.md | 项目结构规划文档 - 5.9

## 其他（gitignore）
- venv/ | Python 虚拟环境 - 5.6
- .ultralytics/ | Ultralytics 框架配置目录
```

## 不创建标记文件的位置

- `venv/`：gitignore，虚拟环境不需标记
- `data/smoke_dataset/`、`data/factory_dataset/` 等数据集子目录：文件过多（数百个），仅用 `data/4_1_category.txt` 概括
- `ai-detection-ui-design/pages/`、`ai-detection-ui-design/partials/`：仅用 `ai-detection-ui-design/1_category.txt` 概括
- `.trae/specs/nano-config-baseline/`、`.trae/specs/smoke-ai-platform/`：仅用 `.trae/specs/4_4_category.txt` 概括

## 提议改动

仅创建 19 个 `_category.txt` 文件，**不修改任何现有文件，不改动任何代码**。

### 创建顺序

1. 分区 1：1 个文件（`ai-detection-ui-design/1_category.txt`）
2. 分区 2：6 个文件（`app/2_category.txt` + 5 个子目录）
3. 分区 3：3 个文件（`modules/`、`src/`、`models/`）
4. 分区 4：7 个文件（`data/`、`docs/`、`.trae/documents/`、`.trae/specs/`、`src/jetson/`、`scripts/`、`runs/`）
5. 分区 5：1 个文件（`configs/5_1_category.txt`）
6. 根目录：1 个文件（`0_root_category.txt`）

## 假设与决策

1. **文件名格式**：`<分类号>_category.txt`，多级用下划线连接（如 `2_2_category.txt`）
2. **内容只记当前层**：不递归子目录（如 `data/4_1_category.txt` 不列出数百个图片文件）
3. **全部文件列出**：包括 `__init__.py`，标注为"Python 包标识文件"
4. **内容与 PROJECT_STRUCTURE.md 一致**：描述文字直接引用 PROJECT_STRUCTURE.md
5. **runs/ 目录也创建标记**：虽然被 gitignore，但本地仍需可见分类
6. **根目录创建 0_root_category.txt**：记录散落在根目录的文件分类

## 验证步骤

1. **文件存在性验证**：
   - 检查 19 个 `_category.txt` 文件是否全部创建
   - 用 Glob 工具搜索 `*_category.txt` 确认数量

2. **内容格式验证**：
   - 每个文件以 `# <分类号> <名称>` 开头
   - 文件部分用 `## 文件` 标题
   - 子目录部分用 `## 子目录` 标题
   - 说明部分用 `## 说明` 标题

3. **一致性验证**：
   - 抽查 3 个文件，确认内容与 PROJECT_STRUCTURE.md 描述一致
   - 确认未修改任何现有文件

4. **可选 Git 提交**：
   - `git add *_category.txt`
   - `git commit -m "docs: 添加文件夹分类标记文件（19个）"`

## 实施步骤

1. 批量创建 19 个 `_category.txt` 文件（按上述清单内容）
2. 用 Glob 验证文件数量
3. 抽查 3 个文件内容格式
4. （可选）Git 提交
