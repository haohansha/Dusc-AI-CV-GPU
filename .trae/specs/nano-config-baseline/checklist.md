# Checklist — Nano 环境配置匹配与全局化

## 模型配置匹配检查
- [x] `docs/JETSON_NANO_DEPLOY.md` 新增"已确认的环境基线"小节，记录 Nano 实际环境参数
- [x] 文档明确结论：当前模型配置（imgsz=640/half=True/device=0/workspace=4）与 Nano 环境完全匹配
- [x] 文档列出 ultralytics 8.3.252 与 Windows 端版本兼容性确认

## 全局配置写入
- [x] `app/models/app_config.py` 的 `DEFAULTS` 新增 `jetson` 段，含全部 11 个字段
- [x] `configs/app_config.json` 实际写入 Nano 环境参数（TensorRT="10.3.0" 等）
- [x] `AppConfig` 的 `get("jetson")` 能正确返回配置字典（已实测：tensorrt=10.3.0/imgsz=640/half=True/precision=FP16）
- [x] 原有配置字段（theme/language/window_geometry 等）未被破坏

## 导出引擎接入
- [x] `ExportConfig` 新增 `from_app_config()` 类方法，能从 `AppConfig` 构造配置
- [x] `ExportEngine.__init__` 接受可选 `app_config` 参数
- [x] AppConfig 不可用时回退到原硬编码默认值（imgsz=640/half=True/device=0/workspace=4）
- [x] `app/ui/deploy_page.py` 控件初始值取自 `AppConfig.jetson`
- [x] 部署页面显示"目标 Nano 环境：TensorRT 10.3.0 / Ultralytics 8.3.252 / OpenCV 4.11.0"
- [x] `main_window.py` 将 `app_config` 传入 `ExportEngine` 与 `DeployPage`

## 脚本修正
- [x] `setup_jetson.sh` 标题不再包含 "Orin"
- [x] CUDA 不可用提示改为 "Please flash JetPack (4.6.x for Nano, 6.x for Orin Nano)"
- [x] 脚本仍为纯检测，不安装任何东西

## 回归验证
- [x] `python -c "from app.models.app_config import AppConfig; ..."` 能读到 jetson 配置段（已实测输出：10.3.0 / 8.3.252 / 4.11.0 / imgsz=640 / half=True / precision=FP16）
- [ ] Git 提交包含所有修改文件（待用户确认是否提交）
