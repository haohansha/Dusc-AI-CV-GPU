# Jetson Nano 部署说明文档

本文档指导你将 Windows 上微调后的烟雾检测模型部署到 Jetson Nano，并使用 CSI 摄像头实时测试模型效果。

---

## 1. 概述与前置条件

### 硬件
- Jetson Nano（B01 / 2GB / 4GB 均可）
- CSI 摄像头（树莓派摄像头 IMX219，或 IMX477）
- 传输方式：U盘 / SCP（网络）/ 共享文件夹 任选其一
- 电源：建议 5V/4A DC 供电（MAXN 模式必需）

### 软件
- JetPack 4.6.x（Nano A01/B01）或 JetPack 5.x（Nano 2GB 新版）
- Python 3.6+（JetPack 自带）
- 已安装的 CUDA + TensorRT（JetPack 默认包含）

---

## 2. ⚠️ 重要：TensorRT engine 平台绑定说明

> **关键限制：在 Windows GPU 上导出的 `.engine` 文件不能在 Jetson Nano 上运行。**

### 原因
- CUDA 计算能力不同（Windows GPU 通常 sm_75+，Nano 为 sm_53/87）
- TensorRT 版本不同（Windows 用的 TensorRT 与 JetPack 自带版本不兼容）
- GPU 架构、驱动、运行时均不同

### 正确流程
```
Windows: 微调生成 .pt 模型
        ↓ 传输 .pt
Jetson Nano: 用 .pt 在本地导出 .engine
        ↓
Jetson Nano: 用 .engine 运行推理
```

> 因此，**不要使用 Windows GUI 的"导出 TensorRT"功能**为 Nano 生成 engine。应按本文档步骤在 Nano 上本地导出。

---

## 3. 步骤一：先检查 Nano 环境配置（优先执行）

> 设计理念：先确认 Nano 目标环境是否足够运行 YOLOv8，再据此在 Windows 上调整模型，避免模型与环境不匹配返工。

### 3.1 将项目脚本拷到 Nano

至少先拷贝这两个文件到 Nano（例如 `~/smoke/`）：
- `scripts/setup_jetson.sh`
- `requirements_jetson.txt`

### 3.2 运行环境检查脚本

```bash
cd ~/smoke
bash setup_jetson.sh
```

脚本为**纯检测**，依次检查 JetPack / CUDA / TensorRT / ultralytics / opencv-python / CSI 摄像头，不自动安装任何依赖。

若检测到 ultralytics 或 opencv-python 未安装，脚本会输出 WARNING 并提示手动执行：

```bash
pip3 install -r requirements_jetson.txt
```

安装完成后再次运行 `bash setup_jetson.sh` 确认全部 OK。

### 3.3 逐项验证

```bash
# 1. CUDA 可用性
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
# 期望输出: CUDA: True

# 2. TensorRT 版本
python3 -c "import tensorrt; print('TensorRT:', tensorrt.__version__)"

# 3. YOLOv8 可运行
python3 -c "from ultralytics import YOLO; print('ultralytics: OK')"

# 4. CSI 摄像头设备节点
ls /dev/video*
# 期望看到 video0

# 5. CSI 摄像头预览测试（按 Esc 退出）
nvgstcapture-1.0 --prev-res=3
```

### 3.4 决策分支

- ✅ **若以上全部通过**（CUDA=True、TensorRT 有版本号、ultralytics OK、CSI 能预览）
  → 进入步骤二，按 Nano 环境在 Windows 上调整模型

- ❌ **若实在不符合**（如 CUDA=False、缺包、CSI 无画面）
  → 先调整 Nano 环境：
  - CUDA 不可用：重刷 JetPack 4.6.x（含 CUDA + TensorRT + cuDNN）
  - 缺 ultralytics：`pip3 install ultralytics`
  - CSI 无画面：检查排线、运行 `nvgstcapture-1.0`、确认 `ls /dev/video0` 存在
  - 调整完毕后回到本步骤重新验证，通过后再进入步骤二

### 3.5 已确认的环境基线（本次实测）

#### Nano 实际环境参数

| 项目 | 实测值 | 状态 |
|------|--------|------|
| CUDA | 可用 | OK |
| TensorRT | 10.3.0 | OK |
| Ultralytics | 8.3.252 | OK |
| OpenCV | 4.11.0 | OK |
| CSI 摄像头 | /dev/video0 存在 | OK |

#### 模型参数匹配结论

| 模型参数 | 当前值 | Nano 兼容性 |
|----------|--------|--------------|
| imgsz | 640 | ✅ Nano 4GB 可运行 |
| half (FP16) | True | ✅ TensorRT 10.3.0 支持 FP16 |
| device | 0 | ✅ 单 GPU |
| workspace | 4 GB | ✅ 默认即可 |
| ultralytics 版本 | 8.3.252 | ✅ 与 Windows 端 ≥8.3.0 兼容 |

> **结论：** 当前模型配置与 Nano 环境完全匹配，可直接进入步骤三传输文件 + 步骤四在 Nano 上本地导出 .engine。

---

## 4. 步骤二：在 Windows 上按 Nano 环境调整模型准备

### 4.1 确认微调后的模型

在 Windows 项目目录下确认你的微调模型，例如：
```
models/smoke_detection_best.pt
```
> 请用 `--model` 指定你实际微调后的文件名，文档示例统一用 `smoke_detection_best.pt`。

### 4.2 根据 Nano 环境对齐模型参数

| 参数 | Nano 推荐值 | 说明 |
|------|-------------|------|
| 输入分辨率 imgsz | 640（4GB）/ 320（2GB，低配加速） | 与导出 engine 时的 imgsz 保持一致 |
| 类别名 | 必须包含 `smoke` | `smoke_detect.py` 按类名包含 `smoke` 判定 |
| 精度 | FP16（`half=True`） | Nano 支持 FP16，速度约为 FP32 的 2 倍 |

检查类别名：
```bash
python -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); print(m.names)"
```
若类名不是 `smoke`，需在 Windows 上重新微调时使用正确的类名。

### 4.3 需传输到 Nano 的文件清单

| 源文件（Windows） | 目标（Nano） | 用途 |
|-------------------|-------------|------|
| `models/smoke_detection_best.pt` | `~/smoke/models/` | 模型权重（用于在 Nano 上导出 engine） |
| `src/jetson/smoke_detect.py` | `~/smoke/` | 推理脚本 |
| `scripts/setup_jetson.sh` | `~/smoke/` | 环境检查（已在步骤一传输） |
| `requirements_jetson.txt` | `~/smoke/` | 依赖清单（已在步骤一传输） |

---

## 5. 步骤三：传输文件到 Jetson Nano

### 方案A：U盘拷贝（最简单）
1. 将上述文件拷入 U盘
2. 插入 Nano，复制到 `~/smoke/`

### 方案B：SCP（网络传输）
```bash
# 在 Windows 上执行（替换 nano_ip 和用户名）
scp -r models/smoke_detection_best.pt user@nano_ip:~/smoke/models/
scp src/jetson/smoke_detect.py user@nano_ip:~/smoke/
```

### 目标目录结构
```
~/smoke/
├── smoke_detect.py
├── setup_jetson.sh
├── requirements_jetson.txt
└── models/
    └── smoke_detection_best.pt
```

---

## 6. 步骤四：在 Nano 上导出 TensorRT engine（本地导出）

> 必须在 Nano 上本地导出，engine 才能与 Nano 的 GPU 架构匹配。

### 6.1 一行命令导出

```bash
cd ~/smoke
python3 -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); m.export(format='engine', imgsz=640, half=True, device=0)"
```

### 6.2 说明
- `half=True`：FP16 精度，Nano 推理速度约为 FP32 的 2 倍
- `imgsz=640`：需与模型微调时的输入尺寸一致
- `device=0`：使用 Nano GPU
- 导出耗时：Nano 上约 **5-15 分钟**，期间会下载/优化算子，请耐心等待

### 6.3 后备方案：ONNX
若 TensorRT 导出失败，可先导出 ONNX：
```bash
python3 -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); m.export(format='onnx', imgsz=640, half=True)"
```
然后用 ONNX Runtime 推理（速度较慢）。

### 6.4 验证 engine 生成
```bash
ls -lh models/smoke_detection_best.engine
# 应看到生成的 .engine 文件，大小约 6-10MB
```

---

## 7. 步骤五：用 CSI 摄像头测试模型

### 方法A（首选）：直接用 `--camera 0`

```bash
cd ~/smoke
python3 smoke_detect.py --model models/smoke_detection_best.engine --camera 0
```
> JetPack 默认 OpenCV 若编译了 Argus 后端，`--camera 0` 可直接走 CSI。

### 方法B（若 A 失败）：先确认 CSI 摄像头工作

```bash
nvgstcapture-1.0 --prev-res=3
```
能看到预览说明 CSI 硬件正常，问题在 OpenCV 后端 → 用方法 C。

### 方法C（GStreamer 管道）：用代码片段打开 CSI

新建 `csi_test.py`：
```python
import cv2, sys
sys.path.insert(0, '.')
from smoke_detect import SmokeDetector

pipeline = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM),width=1280,height=720,format=NV12,framerate=30/1 ! "
    "nvvidconv ! video/x-raw,format=BGRx ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("CSI 摄像头打开失败"); sys.exit(1)

detector = SmokeDetector('models/smoke_detection_best.engine', conf=0.3)
print("CSI 已就绪，按 Ctrl+C 停止")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    result = detector.detect(frame)
    print(f"smoke={result['has_smoke']} level={result['level']} {result['inference_ms']:.1f}ms")
cap.release()
```
运行：
```bash
python3 csi_test.py
```

### 测试其他输入源
```bash
# 视频文件
python3 smoke_detect.py --model models/smoke_detection_best.engine --video test.mp4

# RTSP 流
python3 smoke_detect.py --model models/smoke_detection_best.engine --rtsp rtsp://admin:pass@192.168.1.100:554/Streaming/Channels/101

# 调整置信度阈值
python3 smoke_detect.py --model models/smoke_detection_best.engine --camera 0 --conf 0.4
```

---

## 8. 步骤六：性能调优

### 8.1 功率模式
```bash
# 切到 MAXN 最高性能（需 DC 5V/4A 供电）
sudo nvpmodel -m 0
sudo jetson_clocks

# 查看当前模式
sudo nvpmodel -q
```

### 8.2 精度与分辨率影响
| 配置 | Nano 4GB 预期 FPS |
|------|-------------------|
| FP16 + imgsz 640 | 25-40 FPS |
| FP32 + imgsz 640 | 12-20 FPS |
| FP16 + imgsz 320 | 50-70 FPS |

### 8.3 监控资源
```bash
# GPU 占用
tegrastats
# 关注 GR3D_FREQ 和 RAM 使用
```

---

## 9. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `cv2.VideoCapture(0)` 打不开 CSI | OpenCV 未带 Argus 后端 | 用方法 C 的 GStreamer 管道 |
| TensorRT 导出失败 | JetPack 版本过旧 / 磁盘空间不足 | 确认 JetPack 4.6+；清理 `~/.cache`；预留 ≥2GB 空间 |
| `Out of memory` | Nano 显存不足 | 降低 imgsz 到 320；或用 4GB 版本 |
| 模型类别名不匹配 | 微调时类名非 `smoke` | 检查 `m.names`；重新微调用 `smoke` 类名 |
| CSI 摄像头未识别 | 排线松动 / 设备节点未生成 | 检查排线；`ls /dev/video0`；重启 |
| `nvgstcapture` 无画面 | Argus 服务异常 | `sudo systemctl restart nvargus-daemon` |
| 推理结果全为空 | 置信度阈值过高 | 降低 `--conf 0.2` |
| engine 文件跨设备不可用 | 平台绑定 | 必须在每台 Nano 上单独导出 |

---

## 10. 快速命令速查表

```bash
# === 环境检查 ===
bash setup_jetson.sh
python3 -c "import torch; print(torch.cuda.is_available())"
python3 -c "import tensorrt; print(tensorrt.__version__)"
ls /dev/video*

# === 模型导出（在 Nano 上本地执行）===
python3 -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); m.export(format='engine', imgsz=640, half=True, device=0)"

# === CSI 摄像头测试 ===
python3 smoke_detect.py --model models/smoke_detection_best.engine --camera 0

# === 视频文件测试 ===
python3 smoke_detect.py --model models/smoke_detection_best.engine --video test.mp4

# === 性能模式 ===
sudo nvpmodel -m 0
sudo jetson_clocks
tegrastats

# === 重启 Argus 服务（CSI 异常时）===
sudo systemctl restart nvargus-daemon
```

---

## 附录：模型类别名检查

在 Windows 或 Nano 上均可运行：
```bash
python3 -c "from ultralytics import YOLO; m=YOLO('models/smoke_detection_best.pt'); print(m.names)"
```
期望输出类似：`{0: 'smoke'}`。若类名不是 `smoke`，`smoke_detect.py` 的风扇分级逻辑不会触发。
