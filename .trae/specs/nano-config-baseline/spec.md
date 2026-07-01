# Nano 环境配置匹配与全局化 Spec

## Why

用户已在 Jetson Nano 上运行 `setup_jetson.sh`，确认环境为：CUDA OK / TensorRT 10.3.0 / Ultralytics 8.3.252 / opencv 4.11.0 / CSI camera OK。当前项目模型导出/训练参数分散硬编码在 `ExportConfig`、`TrainingConfig` 中，且 `app_config.json` 没有 Nano 部署相关配置，导致后续开发时无法以 Nano 环境为统一基准。需要一次性将 Nano 环境参数写入全局配置，作为后续所有导出/部署功能的基础。

## What Changes
- 在 `AppConfig.DEFAULTS` 与 `configs/app_config.json` 中新增 `jetson` 配置段，固化 Nano 环境参数（TensorRT/Ultralytics/OpenCV 版本 + imgsz/half/device/workspace/camera 等部署默认值）
- 修改 `modules/export_engine.py` 的 `ExportConfig`：从 `AppConfig` 读取 Nano 部署默认值（imgsz/half/device/workspace），不再使用硬编码
- 修改 `app/ui/deploy_page.py`：模型导出时使用 `AppConfig` 中的 Nano 配置作为默认值，状态栏显示 Nano 环境信息
- 修改 `scripts/setup_jetson.sh`：标题统一为 "Jetson Nano"（不限定 Orin），将硬编码 "JetPack 6.x" 提示改为基于检测结果的动态提示
- 修改 `docs/JETSON_NANO_DEPLOY.md`：在"步骤一"后补充"已确认的环境基线"小节，记录 Nano 实际环境参数，便于后续开发对照

## Impact
- Affected specs: `smoke-ai-platform`（GUI 部署页面行为变化，导出默认值改为读取全局配置）
- Affected code:
  - `app/models/app_config.py`（新增 jetson 配置段）
  - `configs/app_config.json`（写入实际 Nano 环境参数）
  - `modules/export_engine.py`（ExportConfig 从 AppConfig 取默认值）
  - `app/ui/deploy_page.py`（读取 AppConfig 的 Nano 配置作为默认值）
  - `scripts/setup_jetson.sh`（标题与提示文本修正）
  - `docs/JETSON_NANO_DEPLOY.md`（补充环境基线小节）

---

## ADDED Requirements

### Requirement: Nano 部署全局配置
系统 SHALL 在 `AppConfig` 中维护一个 `jetson` 配置段，固化已检测的 Nano 环境参数与部署默认值，作为所有导出/部署功能的基础配置。

#### Scenario: 应用首次启动加载 Nano 配置
- **WHEN** 应用启动并加载 `configs/app_config.json`
- **THEN** `AppConfig` 的 `jetson` 段包含以下字段且非空：
  - `tensorrt_version` = "10.3.0"
  - `ultralytics_version` = "8.3.252"
  - `opencv_version` = "4.11.0"
  - `imgsz` = 640
  - `half` = true
  - `device` = 0
  - `workspace` = 4
  - `precision` = "FP16"
  - `camera_type` = "csi"
  - `camera_index` = 0
  - `camera_pipeline` = ""（空表示用 `--camera 0`，非空则用 GStreamer 管道）

#### Scenario: 部署页面使用 Nano 配置作为默认值
- **WHEN** 用户打开"Jetson部署"页面
- **THEN** 模型选择、分辨率(640)、精度(FP16)、Workspace(4) 等控件初始值取自 `AppConfig.jetson`
- **AND** 状态栏或页面顶部显示"目标 Nano 环境：TensorRT 10.3.0 / Ultralytics 8.3.252 / OpenCV 4.11.0"

---

## MODIFIED Requirements

### Requirement: 模型导出引擎默认值
`ExportConfig` 的 `imgsz`/`half`/`device`/`workspace` 默认值 SHALL 从 `AppConfig.jetson` 读取，而非硬编码。当 `AppConfig` 不可用时回退到原硬编码默认值（imgsz=640, half=True, device=0, workspace=4）。

#### Scenario: 调用导出引擎
- **WHEN** 调用 `ExportEngine.export_tensorrt()` 且未显式传入 `config`
- **THEN** 系统构造 `ExportConfig` 时，`imgsz`/`half`/`device`/`workspace` 取自 `AppConfig.jetson`
- **AND** 导出命令附加 `version` 字段备注（r10.3.0 兼容性已确认）

### Requirement: setup_jetson.sh 检测脚本
脚本 SHALL 不再硬编码"JetPack 6.x"字样；CUDA 不可用时提示"请重刷 JetPack（建议 4.6.x 或 6.x 视设备型号）"，让用户按设备型号选择。

#### Scenario: CUDA 不可用
- **WHEN** `python3 -c "import torch; print(torch.cuda.is_available())"` 返回 False
- **THEN** 脚本输出 `WARNING: CUDA not available. Please flash JetPack (4.6.x for Nano, 6.x for Orin Nano)`
- **AND** 不影响其他检测项继续执行
