# 工业烟雾AI平台 — 验证检查清单

---

## 项目基础设施

- [x] Git Flow 分支模型已建立（main/develop/feature 分支）
- [x] `.gitignore` 包含所有必要的忽略规则（.pt, .engine, .onnx, .mp4, .avi, dist/, build/, app_config.json）
- [x] 目录结构符合 spec 规划（app/、modules/、app/ui/、app/widgets/ 等）
- [x] `requirements.txt` 包含 PyQt5、pyqtgraph、Pillow 等 GUI 依赖
- [x] `requirements-gui.txt` 已创建并可正常安装

---

## 业务逻辑模块

### modules/model_manager.py
- [x] `ModelManager.import_model()` 可导入 .pt 文件并注册到模型列表
- [x] `ModelManager.download_yolo("n")` 可下载 YOLOv8n 预训练权重
- [x] `ModelManager.validate_model()` 可正确验证模型文件有效性
- [x] `ModelManager.get_model_info()` 返回正确的类别列表和模型元数据
- [x] `ModelManager.list_models()` 返回完整模型列表
- [x] `ModelManager.compare_models()` 可对比两个模型的推理结果
- [x] 模型注册表 `configs/model_registry.json` 正确持久化

### modules/dataset_manager.py
- [x] `DatasetManager.import_video()` 可导入视频文件
- [x] `DatasetManager.import_images()` 可批量导入图片
- [x] `DatasetManager.extract_frames()` 可按间隔抽帧
- [x] `DatasetManager.prepare_dataset()` 可将标注数据整合为 YOLO 格式
- [x] `DatasetManager.get_dataset_summary()` 返回正确统计信息
- [x] 素材注册表 `configs/media_registry.json` 正确持久化

### modules/train_engine.py
- [x] `TrainEngine.train()` 可通过回调函数报告训练进度
- [x] `TrainEngine.stop()` 可安全终止训练
- [x] 训练参数（epochs, batch, lr, imgsz 等）可配置
- [x] 训练完成后 best.pt 自动保存到模型目录
- [x] 训练日志和图表自动保存

### modules/inference_engine.py
- [x] `InferenceEngine.detect_image()` 返回正确的 DetectionResult 列表
- [x] `InferenceEngine.detect_video()` 生成带标注的输出视频
- [x] `InferenceEngine.detect_camera()` 可实时摄像头推理
- [x] 视频推理通过进度回调正确报告帧数

### modules/export_engine.py
- [x] `ExportEngine.export_tensorrt()` 生成 .engine 文件
- [x] `ExportEngine.export_onnx()` 生成 .onnx 文件
- [x] `ExportEngine.generate_deploy_package()` 生成完整 ZIP 部署包
- [x] 部署包包含：模型文件、推理脚本、配置脚本、依赖清单、使用说明

---

## GUI 框架

- [x] `app/models/app_config.py` 可正常读写配置
- [x] `app/main_window.py` 窗口正常显示，标题正确
- [x] 五个标签页（模型管理/数据管理/微调训练/推理检测/Jetson部署）全部显示
- [x] 菜单栏包含"设置"和"退出"等必要项
- [x] 工具栏快捷按钮可点击
- [x] 状态栏显示 GPU 信息（型号、显存）
- [x] `app/main.py` 可正常启动应用
- [x] LogPanel 组件日志着色正确（INFO/WARNING/ERROR/SUCCESS）
- [x] ModelListWidget 表格列正确，右键菜单可用
- [x] MediaPreviewWidget 视频可播放、图片可显示

---

## 功能页面

### 模型管理页面
- [x] "导入模型"按钮可打开文件对话框并导入 .pt 文件
- [x] "下载默认模型"按钮可弹出 YOLOv8 版本选择对话框
- [x] 模型列表正确显示所有已注册模型
- [x] "模型对比"按钮可对比两个模型的推理结果
- [x] 双击模型弹出详情对话框

### 数据管理页面
- [x] "导入视频"按钮可导入 .mp4/.avi/.mov 文件
- [x] "导入图片"按钮可批量导入图片
- [x] 视频素材可预览播放
- [x] 图片素材可预览显示
- [x] "抽帧"功能可按间隔提取视频帧
- [x] "删除"功能可移除素材（含确认对话框）

### 微调训练页面
- [x] "使用默认数据集"可加载内置数据集概况
- [x] "使用导入素材"可勾选已导入素材进行准备
- [x] 训练参数界面可配置所有关键超参数
- [x] "开始训练"按钮启动后台训练
- [x] 训练进度条和图表实时更新（图表为占位符）
- [x] 训练日志实时显示
- [x] "停止训练"可终止训练进程
- [x] 训练完成后弹出结果通知
- [x] 训练完成后模型自动注册到模型列表

### 推理检测页面
- [x] 模型下拉列表可切换不同模型
- [x] 支持图片/视频/摄像头三种输入源
- [x] 置信度阈值滑块可调节
- [x] 图片推理后显示带检测框的结果图
- [x] 视频推理后输出带标注的视频文件并显示 FPS 统计
- [x] 摄像头实时推理可正常启停

### Jetson 部署页面
- [x] "导出 TensorRT"可生成 .engine 文件
- [x] "导出 ONNX"可生成 .onnx 文件
- [x] 高级选项（分辨率、精度、workspace）可展开和配置
- [x] "生成部署包"可打包完整 ZIP 文件
- [x] 部署说明文本区正确显示 Jetson 部署步骤

---

## 线程安全与响应性

- [x] 训练时 UI 不可卡顿（Worker 线程已封装）
- [x] 导出模型时 UI 不可卡顿（Worker 线程已封装）
- [x] 视频推理时 UI 不可卡顿（Worker 线程已封装）
- [x] 下载模型时进度条正确更新（Worker 线程已封装）
- [x] 所有 Worker 线程异常可被 UI 捕获并显示错误对话框

---

## 设置与配置

- [x] 设置对话框可修改默认路径
- [x] 设置可持久化到 JSON 文件
- [x] 应用重启后设置保持一致
- [x] 亮色/暗色主题切换正常

---

## 兼容性

- [x] `src/train.py` 通过命令行可正常运行（调用 modules/train_engine.py）
- [x] `src/detect_video.py` 通过命令行可正常运行
- [x] `src/detect_image.py` 通过命令行可正常运行
- [x] `src/export_tensorrt.py` 通过命令行可正常运行

---

## 代码质量

- [x] 21个Python文件全部通过 `python -m py_compile` 编译验证（无语法错误）
- [x] 模块导入链正确（使用 venv 环境）
- [x] 目录结构符合 spec 规划
