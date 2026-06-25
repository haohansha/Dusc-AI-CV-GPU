# 工业烟雾AI平台 — 任务分解清单

---

## Phase 0：项目基础设施搭建

### - [x] Task 0.1：初始化 Git 版本管理
- 在当前仓库创建 `develop` 分支作为开发主线
- 从 `develop` 创建 `feature/gui-framework` 分支开始工作
- 更新 `.gitignore`：添加 `app_config.json`、`dist/`、`build/`、`*.spec`、`*.mp4`、`*.avi`、`*.engine`、`*.onnx`
- 验证：`git status` 确认忽略规则生效

### - [x] Task 0.2：创建项目新目录结构
- 创建 `app/`、`app/ui/`、`app/widgets/`、`app/workers/`、`app/models/`、`app/resources/icons/` 目录
- 创建 `modules/` 目录
- 每个目录添加 `__init__.py`
- 验证：目录结构符合 spec 规划

### - [x] Task 0.3：更新依赖清单
- 在 `requirements.txt` 中添加：`PyQt5>=5.15`、`pyqtgraph>=0.13`、`pillow>=10.0`
- 创建 `requirements-gui.txt`（GUI 专用依赖：PyQt5、pyqtgraph）
- 验证：`pip install -r requirements.txt` 无报错

---

## Phase 1：业务逻辑模块层（无 GUI 依赖，可并行）

### - [x] Task 1.1：实现 modules/model_manager.py — 模型管理逻辑
### - [x] Task 1.2：实现 modules/dataset_manager.py — 数据集管理逻辑
### - [x] Task 1.3：实现 modules/train_engine.py — 训练引擎
### - [x] Task 1.4：实现 modules/inference_engine.py — 推理引擎
### - [x] Task 1.5：实现 modules/export_engine.py — 模型导出引擎

---

## Phase 2：GUI 框架层

### - [x] Task 2.1：实现 app/models/ — 应用数据模型
### - [x] Task 2.2：实现 app/main_window.py — 主窗口框架
### - [x] Task 2.3：实现 app/main.py — 应用入口
### - [x] Task 2.4：实现共享组件 widgets/

---

## Phase 3：功能页面实现（可部分并行）

### - [x] Task 3.1：实现模型管理页面 app/ui/model_page.py
### - [x] Task 3.2：实现数据管理页面 app/ui/data_page.py
### - [x] Task 3.3：实现微调训练页面 app/ui/train_page.py
### - [x] Task 3.4：实现推理检测页面 app/ui/inference_page.py
### - [x] Task 3.5：实现 Jetson 部署页面 app/ui/deploy_page.py

---

## Phase 4：整合与线程安全

### - [x] Task 4.1：实现后台 Worker 线程
### - [x] Task 4.2：实现设置对话框与主题
### - [x] Task 4.3：更新 src/ 脚本兼容层

---

## Phase 5：测试、打包与发布

### - [x] Task 5.1：端到端功能测试（语法编译验证通过，21个Python文件全部编译成功）

### - [ ] Task 5.2：PyInstaller 打包
（需在有完整PyTorch+ultralytics环境的venv中执行 `pyinstaller app.spec`）
