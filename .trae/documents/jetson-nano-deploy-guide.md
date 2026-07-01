# Jetson Nano 部署说明文档 - 实现计划

## 概述

用户已有 Jetson Nano 硬件并连接了 CSI 摄像头，希望将微调后的模型部署到 Nano 上测试效果。需创建一份详细的部署说明文档，覆盖：模型传输、环境配置、TensorRT 本地导出、CSI 摄像头测试、性能调优、故障排查。

## 当前状态分析

通过阅读源码确认现有部署资产：

| 资产 | 位置 | 用途 | 现状 |
|------|------|------|------|
| Jetson 推理脚本 | [src/jetson/smoke_detect.py](file:///e:/project/Dusc%20AI%20CV%20GPU/src/jetson/smoke_detect.py) | 在 Nano 上运行烟雾检测 | 支持 --video/--camera/--rtsp/--model/--conf；含风扇分级控制逻辑 |
| 环境配置脚本 | [scripts/setup_jetson.sh](file:///e:/project/Dusc%20AI%20CV%20GPU/scripts/setup_jetson.sh) | 检查 JetPack/CUDA/TensorRT + 安装依赖 | 已实现 4 步检查 |
| Jetson 依赖清单 | [requirements_jetson.txt](file:///e:/project/Dusc%20AI%20CV%20GPU/requirements_jetson.txt) | ultralytics + opencv-python | 已定义 |
| 模型导出引擎 | [modules/export_engine.py](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/export_engine.py) | 导出 TensorRT/ONNX + 生成部署包 | Windows 端导出，但 engine 跨平台不兼容 |
| GUI 部署页面 | [app/ui/deploy_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/deploy_page.py) | 可视化导出 | 同上 |

### 两个关键约束（必须在文档中强调）

1. **TensorRT engine 平台绑定**：Windows GPU 导出的 `.engine` 文件**不能**在 Jetson Nano 上运行。原因：
   - CUDA 计算能力不同（Windows GPU vs Nano 的 Maxwell/Ampere）
   - TensorRT 版本不同
   - 必须在 Nano 上用 `.pt` 本地导出 `.engine`

2. **CSI 摄像头特殊处理**：`smoke_detect.py` 当前用 `cv2.VideoCapture(int)` 打开摄像头。对 CSI 摄像头：
   - JetPack 默认 OpenCV 编译了 GStreamer 支持时，`--camera 0` 可能直接可用（走 Argus 后端）
   - 若不可用，需用 GStreamer 管道字符串（`nvarguscamerasrc`）
   - 当前脚本 `--camera` 是 int 类型，不支持传 GStreamer 字符串

### 模型文件现状

- `models/smoke_detection_best.pt` 存在（微调后的模型）
- `smoke_detect.py` 默认模型名 `factory_smoke_finetuned.pt`（与实际文件名不一致，文档中需提示用 `--model` 指定实际文件名）

## 实现方案

### 唯一交付物：创建部署说明文档

**文件**：`docs/JETSON_NANO_DEPLOY.md`（新建 docs 目录）

**不修改任何代码**（用户只要说明文件；CSI 摄像头的 GStreamer 方案在文档中以命令/代码片段形式提供，用户可自行选用）

#### 文档结构（10 个章节）

**1. 概述与前置条件**
- 硬件：Jetson Nano（B01/2GB/4GB）+ CSI 摄像头（IMX219/IMX477）+ 网络/USB 传输方式
- 软件：JetPack 4.6.x（Nano）/5.x（Nano 2GB 新版）+ 已安装 Python3

**2. ⚠️ 重要：TensorRT engine 平台绑定说明**
- 解释为什么不能在 Windows 导出 engine 后拷到 Nano
- 正确流程图：`.pt` → 传到 Nano → 在 Nano 上导出 `.engine` → 运行

**3. 步骤一：先检查 Nano 环境配置（优先执行）**
- 设计理念：先确认 Nano 目标环境，再据此在 Windows 上调整模型，避免模型与环境不匹配返工
- 运行 `bash setup_jetson.sh` 检查 JetPack/CUDA/TensorRT
- 安装依赖 `pip3 install -r requirements_jetson.txt`
- 验证：`python3 -c "import torch; print(torch.cuda.is_available())"` 应输出 True
- 验证：`python3 -c "import tensorrt; print(tensorrt.__version__)"`
- 验证 YOLOv8 可运行：`python3 -c "from ultralytics import YOLO; print('OK')"`
- 检查 CSI 摄像头：`ls /dev/video*` 应看到 video0；`nvgstcapture-1.0 --prev-res=3` 测试
- 决策分支：
  - 若 Nano 环境已足够运行 YOLOv8 → 进入步骤二，按 Nano 环境在 Windows 上调整模型（如对齐 imgsz、确认类别名等）
  - 若实在不符合 → 先调整 Nano 环境（重刷 JetPack / 安装缺失依赖），再回到步骤二

**4. 步骤二：在 Windows 上按 Nano 环境调整模型准备**
- 确认微调后的 `.pt` 模型路径（如 `models/smoke_detection_best.pt`）
- 根据 Nano 环境对齐模型参数：
  - 输入分辨率（Nano 上常用 640，低配可用 320）
  - 确认模型类别名与 `smoke_detect.py` 中 `smoke` 关键字匹配
  - FP16 兼容性（Nano 支持 FP16）
- 列出需传输的文件清单：
  - `models/smoke_detection_best.pt`（模型权重）
  - `src/jetson/smoke_detect.py`（推理脚本）
  - `scripts/setup_jetson.sh`（环境配置）
  - `requirements_jetson.txt`（依赖清单）

**5. 步骤三：传输文件到 Jetson Nano**
- 方案A：U盘拷贝（最简单）
- 方案B：SCP（`scp -r models/ user@nano_ip:~/smoke/`）
- 方案C：共享文件夹
- 目标目录结构示例

**6. 步骤四：在 Nano 上导出 TensorRT engine（本地导出）**
- 一行命令导出：
  ```bash
  python3 -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); m.export(format='engine', imgsz=640, half=True, device=0)"
  ```
- 说明 `half=True`（FP16）对 Nano 的加速意义
- 导出耗时预期（Nano 上约 5-15 分钟）
- 也可用 ONNX 作为后备（`format='onnx'`）

**7. 步骤五：用 CSI 摄像头测试模型**
- **方法A（首选）**：直接用 `--camera 0`
  ```bash
  python3 smoke_detect.py --model models/smoke_detection_best.engine --camera 0
  ```
- **方法B（若 A 失败）**：先用 nvgstcapture 确认 CSI 摄像头工作
  ```bash
  nvgstcapture-1.0 --prev-res=3
  ```
- **方法C（GStreamer 管道）**：提供一段 Python 代码片段，用 GStreamer 管道打开 CSI 摄像头并调用 SmokeDetector
  ```python
  pipeline = ("nvarguscamerasrc ! video/x-raw(memory:NVMM),width=1280,height=720,"
             "format=NV12,framerate=30/1 ! nvvidconv ! video/x-raw,format=BGRx "
             "! videoconvert ! video/x-raw,format=BGR ! appsink drop=1")
  cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
  ```
- 测试其他输入源：
  - 视频文件：`--video test.mp4`
  - RTSP：`--rtsp rtsp://...`

**8. 步骤六：性能调优**
- FP16（`half=True`）vs FP32 的速度差异
- 输入分辨率影响（640→320 可加速但精度下降）
- Nano 功率模式：`sudo nvpmodel -m 0`（MAXN）+ `sudo jetson_clocks`
- 预期 FPS 参考表

**9. 故障排查**
- `cv2.VideoCapture(0)` 打不开 CSI → 用 GStreamer 管道（方法C）
- TensorRT 导出失败 → 检查 JetPack 版本 + 磁盘空间（engine 导出需临时空间）
- `Out of memory` → 降低 imgsz 或用 Nano 4GB 版本
- 模型类别名不匹配 → 检查 `.pt` 的 `model.names`
- CSI 摄像头未识别 → `ls /dev/video*` 应看到 video0；运行 `nvgstcapture-1.0` 测试

**10. 快速命令速查表**
- 环境检查、模型导出、CSI 测试、视频测试、性能监控等常用命令一览

## 假设与决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 交付物 | 仅创建 1 个 .md 文档 | 用户明确"给我一个说明文件" |
| 文档位置 | `docs/JETSON_NANO_DEPLOY.md` | 规范化，与项目根分离 |
| 是否修改 smoke_detect.py | 不修改 | 用户只要说明文件；CSI 的 GStreamer 方案在文档中以代码片段提供，用户可自行选用或粘贴测试 |
| TensorRT 导出位置 | 在 Nano 上本地导出 | engine 跨平台不兼容，必须本地导出 |
| 步骤顺序 | 先检查 Nano 环境 → 再按 Nano 环境调整 Windows 模型 → 传输 → 本地导出 | 用户要求：先确认目标环境再准备模型，避免返工；若 Nano 环境不符合再调整 Nano |
| CSI 摄像头首选方案 | `--camera 0` 优先 | JetPack 默认 OpenCV 常支持 Argus 后端，最简单；失败时再退到 GStreamer 管道 |
| 模型文件名 | 文档中用 `smoke_detection_best.pt` 作为示例 | glob 确认此文件存在；并提示用户用 `--model` 指定自己的实际文件名 |
| 是否覆盖 GUI 部署页面的导出说明 | 不覆盖 | GUI 导出在 Windows 上进行，engine 不可跨平台；文档明确说明此限制 |

## 验证步骤

1. 确认 `docs/JETSON_NANO_DEPLOY.md` 已创建
2. 文档包含全部 10 个章节
3. 步骤一为"先检查 Nano 环境配置"，含决策分支（环境足够→调整模型 / 不符合→调整 Nano 环境）
4. CSI 摄像头部分提供 3 种方法（camera 0 / nvgstcapture / GStreamer 管道）
5. TensorRT 平台绑定限制有显著警告标识
6. 所有命令可直接复制到 Nano 终端执行
7. 故障排查覆盖 CSI/TensorRT/内存常见问题
