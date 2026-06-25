# UI 排版重构 - 实现计划

## 概述

当前首页存在复数个"导入模型"按钮（主窗口工具栏、模型管理页面、ModelListWidget 内部各一组），tab 页过多（5个），且数据管理页面缺少标签管理功能。本计划按已审核通过的设计稿（`.trae/documents/ui-layout-redesign.md`）创建一个**纯 UI Demo**，供用户审核排版。审核通过后再接回真实业务逻辑。

## 当前状态分析

通过阅读源码确认问题根源：

| 问题 | 位置 | 现状 |
|------|------|------|
| 主窗口工具栏重复 | [main_window.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/main_window.py#L82-L88) `_init_toolbar()` | 3个按钮仅切tab，与tab导航重复 |
| ModelListWidget 内部按钮重复 | [model_list.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/widgets/model_list.py#L37-L52) | 内部有"导入模型/下载默认模型/刷新"按钮 |
| 模型管理页面顶部按钮 | [model_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/model_page.py#L32-L47) | 又一组"导入模型/下载默认模型/刷新列表/模型对比" |
| tab 顺序错误 | [main_window.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/main_window.py#L109-L131) | 当前：模型管理→数据管理→微调训练→推理检测→Jetson部署（5个） |
| 微调训练独立 tab | [train_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/train_page.py) | 应合并到模型管理 |
| 数据管理无标签管理 | [media_preview.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/widgets/media_preview.py) | 仅2栏（列表+预览），无标签编辑 |
| torch 导入顺序 | [main.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/main.py#L10-L12) | `import torch` 必须在 PyQt5 之前（DLL加载修复） |

## 实现方案

### 第一步：创建纯 UI Demo（本次实现）

新建 `app/demo.py`，**自包含、不依赖业务模块**，用假数据展示4个tab的全新排版。所有按钮点击仅弹提示框或打印日志。

#### 文件结构

```
app/demo.py  (新建，单文件)
├── DataManagementPage    — 数据管理（三栏：素材列表|预览区|标签管理）
├── ModelManagementPage   — 模型管理（上半模型列表+详情，下半可折叠微调训练）
├── InferenceDemoPage     — 推理检测（左配置|右预览+结果）
├── DeployDemoPage        — Jetson部署（模型选择+导出选项+说明+验证）
└── DemoMainWindow        — 主窗口（菜单栏+状态栏+4tab，无工具栏）
```

#### 各页面实现细节

**1. DemoMainWindow**
- 菜单栏：文件(设置/退出) + 帮助(关于)
- 状态栏：GPU信息 + 模型状态（假数据："GPU: NVIDIA RTX 3060 (12.0 GB)"）
- **无工具栏**（移除 `_init_toolbar`）
- 4个tab，顺序：数据管理 → 模型管理 → 推理检测 → Jetson部署
- 加载暗色主题 `app/resources/dark.qss`

**2. DataManagementPage（数据管理）**
- 顶部按钮栏：`[导入视频] [导入图片] [删除] [启动LabelImg]`（唯一一组）
- 三栏 QSplitter，比例 1:3:1：
  - 左栏：QListWidget 素材列表（假数据：factory.mp4, smoke_01.jpg, smoke_02.jpg, test.avi）
  - 中栏：QLabel 预览区（显示占位文字"图片/视频预览区"，选中图片时显示假标注框示意）
  - 右栏：标签管理面板
    - QLabel "当前图片标签"
    - 假标签列表：`#0 smoke x:0.12 y:0.23 w:0.45 h:0.67 [编辑][删除]`
    - 底部：`[+ 添加标签]` + 类别下拉框 `[smoke ▼]`
    - 视频素材时隐藏标签管理面板
- 底部状态标签："共 4 个素材 | 当前: smoke_01.jpg (2个标签)"

**3. ModelManagementPage（模型管理）**
- 顶部按钮栏：`[导入模型] [下载默认模型] [刷新] [模型对比]`（唯一一组）
- 上半区（QSplitter 上）：
  - 模型列表 QTableWidget（假数据：yolov8n.pt 预训练/80/6.2MB, smoke_best.pt 微调/1/6.1MB, factory.pt 导入/1/6.1MB）
  - 模型详情 QGroupBox（路径/架构/类别/mAP）
- 下半区（QSplitter 下）：可折叠微调训练面板
  - 标题栏：`▼ 微调训练 [折叠/展开]`
  - 左侧：数据源（默认数据集/导入素材单选）+ 基础模型下拉
  - 右侧：训练参数（轮数50/批次8/学习率0.0001/尺寸640）+ 高级选项折叠
  - 底部：`[开始训练] [停止训练]` + 进度条(60%假数据) + 日志面板（3条假日志）

**4. InferenceDemoPage（推理检测）**
- QSplitter 左右 3:7
- 左栏配置面板：
  - 模型选择 `[smoke_best.pt ▼]`
  - 输入源（图片/视频/摄像头单选）+ 素材下拉 + 浏览按钮
  - 置信度滑块 0.25
  - `[开始检测] [停止检测]`
- 右栏：
  - 上：检测画面 QLabel（占位"检测画面预览区"）
  - 下：检测结果 QTableWidget（假数据2行：smoke 85.2%, smoke 72.1%）+ 统计标签

**5. DeployDemoPage（Jetson部署）**
- 顶部按钮栏：`[导出 TensorRT] [导出 ONNX] [生成部署包]`
- 模型选择 `[smoke_best.pt ▼]`
- 高级选项可折叠：分辨率640 / 精度FP16 / Workspace 4GB
- 部署说明 QTextEdit（只读，假步骤文本）
- 验证导出：`[验证导出]` + 结果标签（TensorRT ✓ / ONNX ✓）

#### 所有按钮的占位行为
- 统一 `_placeholder(name)` 方法：`QMessageBox.information(self, "Demo", f"{name} 功能将在审核通过后接入")`
- 不导入任何业务模块（model_manager, dataset_manager, train_engine, inference_engine, export_engine）

#### 启动方式
```
python -m app.demo
```
- `import torch` 在 PyQt5 之前（保持 DLL 加载修复）
- 加载 dark.qss 暗色主题

### 第二步：用户审核通过后（本次不实现）

审核通过后，将按以下顺序修改真实文件：
1. `app/main_window.py` — 移除 `_init_toolbar()`，tab 改为4个并调整顺序
2. `app/widgets/model_list.py` — 移除内部工具栏按钮
3. `app/widgets/media_preview.py` — 改为三栏布局 + 标签管理
4. `app/ui/model_page.py` — 合并 train_page 功能
5. `app/ui/data_page.py` — 适配三栏 + LabelImg 按钮
6. `app/ui/train_page.py` — 废弃
7. `app/ui/inference_page.py` / `app/ui/deploy_page.py` — 统一间距

## 假设与决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Demo 是否单文件 | 单文件 `app/demo.py` | 自包含、易审核、不污染现有代码 |
| Demo 是否复用现有 widget | 不复用，全部内联 | 现有 widget 含业务逻辑依赖，demo需纯净 |
| 假数据来源 | 硬编码在 demo.py 中 | 无需文件IO，启动快 |
| 主题 | 暗色（dark.qss） | 与正式版一致，审核效果真实 |
| torch 导入 | 保留 `import torch` 在最前 | 避免 DLL 加载失败（已验证的修复） |
| 标签管理坐标格式 | YOLO 归一化 x/y/w/h | 与现有标注文件格式一致 |

## 验证步骤

1. 运行 `python -m app.demo`，确认窗口正常启动
2. 确认 tab 顺序：数据管理 → 模型管理 → 推理检测 → Jetson部署
3. 确认主窗口**无工具栏**（只有菜单栏+状态栏+tab）
4. 确认"导入模型"按钮**只在模型管理tab出现一次**
5. 数据管理tab：确认三栏布局（素材列表|预览区|标签管理），选中视频时标签管理隐藏
6. 模型管理tab：确认上半模型列表+详情，下半可折叠微调训练面板
7. 推理检测tab：确认左配置右预览+结果
8. Jetson部署tab：确认模型选择+导出选项+说明+验证
9. 点击任意按钮，确认弹出"将在审核通过后接入"提示（无报错）
10. 提交截图/运行结果给用户审核
