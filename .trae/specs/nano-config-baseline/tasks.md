# Tasks — Nano 环境配置匹配与全局化

## Phase 1：模型配置匹配检查（仅文档）

- [x] Task 1: 在 `docs/JETSON_NANO_DEPLOY.md` 的"步骤一"之后新增"已确认的环境基线"小节
  - [x] 记录 Nano 实际环境：CUDA OK / TensorRT 10.3.0 / Ultralytics 8.3.252 / OpenCV 4.11.0 / CSI camera OK
  - [x] 列出对应模型参数匹配结论：imgsz=640 ✅、half=True(FP16) ✅、device=0 ✅、workspace=4 ✅、ultralytics 版本兼容 ✅
  - [x] 明确结论：当前模型配置与 Nano 环境完全匹配，可直接进入传输+本地导出步骤

## Phase 2：全局配置写入

- [x] Task 2: 在 `app/models/app_config.py` 的 `DEFAULTS` 中新增 `jetson` 配置段
  - [x] 字段：tensorrt_version/ultralytics_version/opencv_version/imgsz/half/device/workspace/precision/camera_type/camera_index/camera_pipeline
  - [x] 默认值按 Nano 实际环境填写（TensorRT="10.3.0" 等）
  - [x] camera_pipeline 默认空字符串（表示用 `--camera 0`）

- [x] Task 3: 更新 `configs/app_config.json` 写入实际 Nano 环境参数
  - [x] 在 JSON 中新增 `jetson` 对象，字段同 Task 2
  - [x] 保留原有字段（theme/language/window_geometry 等）不变

## Phase 3：导出引擎接入全局配置

- [x] Task 4: 修改 `modules/export_engine.py` 的 `ExportConfig`
  - [x] 新增可选类方法 `from_app_config(app_config)`，返回填充了 jetson 配置的 `ExportConfig`
  - [x] 保持原硬编码默认值作为 fallback（AppConfig 不可用时使用）
  - [x] `ExportEngine.__init__` 接受可选 `app_config` 参数，缓存供导出方法使用

- [x] Task 5: 修改 `app/ui/deploy_page.py`
  - [x] 构造时从 `AppConfig.jetson` 读取 imgsz/precision/workspace 作为控件初始值
  - [x] 在页面顶部或状态栏显示"目标 Nano 环境：TensorRT 10.3.0 / Ultralytics 8.3.252 / OpenCV 4.11.0"
  - [x] 导出按钮调用时使用 `ExportConfig.from_app_config(app_config)` 构造配置

## Phase 4：脚本与文档修正

- [x] Task 6: 修改 `scripts/setup_jetson.sh`
  - [x] 标题改为 "Jetson Nano Smoke Detection Environment Check"（去掉 "Orin"）
  - [x] CUDA 不可用提示改为 "Please flash JetPack (4.6.x for Nano, 6.x for Orin Nano)"

# Task Dependencies
- Task 3 依赖 Task 2（DEFAULTS 字段定义后才能写 JSON）
- Task 5 依赖 Task 4（ExportConfig.from_app_config 存在后 deploy_page 才能调用）
- Task 4、Task 6 互相独立，可并行
- Task 1 独立，可最先执行
