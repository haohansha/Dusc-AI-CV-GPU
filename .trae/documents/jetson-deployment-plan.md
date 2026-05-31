# YOLOv8 模型迁移至 Jetson Orin Nano 8GB — 部署方案

## 一、目标

将训练完成的 `factory_smoke_finetuned.pt`（YOLOv8n）模型迁移到 NVIDIA Jetson Orin Nano 8GB，实现：
1. 模型优化：PyTorch → TensorRT 加速（推理速度提升 3-5x）
2. 工业摄像头 RTSP 流 / 本地视频 / USB 摄像头三种输入
3. 模拟风机控制输出（终端日志），验证模型在 Jetson 上完整运行链路

## 二、Jetson Orin Nano 8GB 硬件规格

| 参数 | 值 |
|------|-----|
| GPU | 1024-core NVIDIA Ampere, 40 TOPS (INT8) |
| CPU | 6-core ARM Cortex-A78AE |
| 内存 | 8GB LPDDR5 |
| 功耗 | 7W~15W |
| 存储 | microSD / NVMe SSD |
| 系统 | JetPack 6.x (Ubuntu 22.04 + CUDA 12.x + TensorRT 10.x) |

> YOLOv8n 模型参数仅 3M，推理 8.1 GFLOPs，在 Orin Nano 上预期 **60-100 FPS**（TensorRT FP16），完全满足 ≥15 FPS 实时要求。

## 三、整体迁移流程

```
┌──────────────────────────────────────────────────────────────┐
│  PC (RTX 5060 Ti)                 Jetson Orin Nano            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. factory_smoke_finetuned.pt                                │
│        │                                                      │
│        ▼                                                      │
│  2. Export to TensorRT                                        │
│     └── .engine (~6MB)                                        │
│              │                                                │
│              └─────── 拷贝 ──────────▶  3. /models/           │
│                                               │               │
│  4. src/export_tensorrt.py                   ▼               │
│                                    5. smoke_detect.py        │
│                                     ├── 模型推理              │
│                                     ├── 浓度判定              │
│                                     └── 模拟风机输出(终端日志) │
│                                        │                      │
│                                        ▼                      │
│                                    6. 验证通过标准:           │
│                                    终端打印 🔥 FAN: XX%       │
│                                    avg FPS ≥ 30              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## 四、Step 1：PC 端导出 TensorRT 模型

### 4.1 新建脚本: `src/export_tensorrt.py`

```python
from ultralytics import YOLO

model = YOLO("models/factory_smoke_finetuned.pt")
# 导出 FP16 TensorRT engine (速度快, 精度略降)
model.export(
    format="engine",
    imgsz=640,
    half=True,           # FP16
    device=0,
    workspace=4,         # 4GB workspace
    simplify=True,
)
# 输出: models/factory_smoke_finetuned.engine (~6 MB)
```

### 4.2 同时导出 ONNX（备用，Jetson 端转换）

```python
model.export(format="onnx", imgsz=640, half=True, simplify=True)
# 输出: models/factory_smoke_finetuned.onnx
```

## 五、Step 2：Jetson Orin Nano 环境搭建

### 5.1 刷机 JetPack 6.x

使用 NVIDIA SDK Manager 或直接烧录 JetPack 6.x 镜像到 microSD 卡。

### 5.2 安装 Python 依赖

```bash
# JetPack 6.x 自带 CUDA/PyTorch/TensorRT，只需安装应用层依赖
pip install ultralytics opencv-python pyserial
```

### 5.3 验证环境

```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
python3 -c "from ultralytics import YOLO; print('ultralytics OK')"
python3 -c "import tensorrt; print('TensorRT:', tensorrt.__version__)"
```

## 六、Step 3：Jetson 端部署脚本（纯软件验证，无硬件风机）

### 6.1 `src/jetson/smoke_detect.py` — 核心推理与模拟风机联动

将模型推理、浓度判定、模拟风机输出整合到一个文件中，Jetson 端唯一需要的脚本：

```python
import argparse, cv2, time, sys
from pathlib import Path
from ultralytics import YOLO

# ═══════════════════════════════════════════════
# 模拟风机输出（纯控制台打印，验证用）
# ═══════════════════════════════════════════════
FAN_SPEEDS = {"LIGHT": 20, "MEDIUM": 50, "HEAVY": 100}
prev_level = None

def fan_control(level, conf, area_pct, ms):
    """模拟风机调速 -- 在终端打印控制系统状态"""
    global prev_level
    duty = FAN_SPEEDS.get(level, 0)
    if level != prev_level:
        if level == "NONE":
            print(f"\n{'='*50}")
            print(f"  🛑 FAN STOP  | 无烟雾检测到")
            print(f"{'='*50}")
        else:
            print(f"\n{'='*50}")
            print(f"  🔥 FAN: {duty}% ({level}) | Conf={conf:.2f} | Area={area_pct:.1f}% | {ms:.1f}ms")
            print(f"     模拟动作: GPIO 输出 PWM={duty}% → 风机变频器")
            print(f"{'='*50}")
        prev_level = level


class SmokeDetector:
    def __init__(self, model_path, conf=0.3):
        self.model = YOLO(model_path)
        self.conf = conf
        self.names = self.model.names
        print(f"Model loaded: {Path(model_path).name}")
        print(f"Classes: {self.names}")
        print(f"Confidence threshold: {conf}")

    def detect(self, frame):
        t0 = time.time()
        results = self.model.predict(frame, conf=self.conf, verbose=False, device=0)
        ms = (time.time() - t0) * 1000

        boxes = results[0].boxes
        info = {"has_smoke": False, "detections": [], "inference_ms": ms,
                "level": "NONE", "fan_speed": 0}

        if boxes is not None:
            h, w = frame.shape[:2]
            smoke_confs = []
            smoke_areas = []
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = self.names[cls_id]
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                area_pct = ((x2-x1)*(y2-y1) / (w*h)) * 100
                d = {"class": cls_name, "conf": conf_val,
                     "bbox": [x1, y1, x2, y2], "area_pct": area_pct}
                info["detections"].append(d)
                if "smoke" in cls_name.lower():
                    info["has_smoke"] = True
                    smoke_confs.append(conf_val)
                    smoke_areas.append(area_pct)

            if info["has_smoke"]:
                max_conf = max(smoke_confs)
                max_area = max(smoke_areas)
                if max_area > 20 or max_conf > 0.7:
                    info["level"] = "HEAVY"
                    info["fan_speed"] = 100
                elif max_area > 10 or max_conf > 0.5:
                    info["level"] = "MEDIUM"
                    info["fan_speed"] = 50
                else:
                    info["level"] = "LIGHT"
                    info["fan_speed"] = 20

        return info


# ═══════════════════════════════════════════════
# 主程序 — 支持三种输入模式
# ═══════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Jetson Smoke Detection Demo")
    parser.add_argument("--model", default="models/factory_smoke_finetuned.pt")
    parser.add_argument("--conf", type=float, default=0.3)
    parser.add_argument("--video", help="视频文件路径（本地验证用）")
    parser.add_argument("--camera", type=int, default=0, help="摄像头ID")
    parser.add_argument("--rtsp", help="RTSP 地址")
    args = parser.parse_args()

    detector = SmokeDetector(args.model, args.conf)

    # 选择输入源
    if args.video:
        cap = cv2.VideoCapture(args.video)
        input_name = f"Video: {args.video}"
    elif args.rtsp:
        cap = cv2.VideoCapture(args.rtsp, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        input_name = f"RTSP: {args.rtsp}"
    else:
        cap = cv2.VideoCapture(args.camera)
        input_name = f"Camera #{args.camera}"

    if not cap.isOpened():
        print(f"Error: Cannot open {input_name}")
        sys.exit(1)

    fps_vid = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{input_name} | {w}x{h} | {fps_vid:.1f} FPS")
    print("Press Ctrl+C to stop\n")

    frame_count = 0
    total_ms = 0
    log_interval = 30  # 每30帧打印一次状态摘要

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if args.video:
                    break  # 视频播放完毕
                else:
                    continue  # 摄像头重试

            frame_count += 1
            result = detector.detect(frame)
            total_ms += result["inference_ms"]

            # 检测到烟雾变化时，模拟风机控制
            if result["has_smoke"] or prev_level is not None:
                max_c = max((d["conf"] for d in result["detections"]
                            if "smoke" in d["class"].lower()), default=0)
                max_a = max((d["area_pct"] for d in result["detections"]
                            if "smoke" in d["class"].lower()), default=0)
                fan_control(result["level"], max_c, max_a, result["inference_ms"])

            # 定期统计输出
            if frame_count % log_interval == 0:
                avg_ms = total_ms / frame_count
                fps = 1000 / avg_ms if avg_ms > 0 else 0
                print(f"  [{frame_count:6d} frames] avg {avg_ms:.1f}ms ({fps:.1f} FPS)")

    except KeyboardInterrupt:
        print("\nStopped by user")

    cap.release()
    avg_ms = total_ms / frame_count if frame_count > 0 else 0
    print(f"\n=== Summary ===")
    print(f"Total frames: {frame_count}")
    print(f"Avg inference: {avg_ms:.1f}ms ({1000/avg_ms:.1f} FPS)" if avg_ms > 0 else "")


if __name__ == "__main__":
    main()
```

### 6.2 脚本支持的三种输入模式

| 模式 | 命令 | 用途 |
|------|------|------|
| 本地视频 | `python smoke_detect.py --video test.mp4` | **刷机后首选验证**，用已有工厂视频快速确认模型能跑 |
| USB 摄像头 | `python smoke_detect.py --camera 0` | 接入 USB 摄像头实时验证 |
| RTSP 摄像 | `python smoke_detect.py --rtsp rtsp://...` | 最终对接工业摄像头 |

### 6.3 控制台输出示例

无烟雾时：
```
  [    30 frames] avg 12.5ms (80.0 FPS)
  [    60 frames] avg 12.3ms (81.3 FPS)
  [    90 frames] avg 12.1ms (82.6 FPS)
```

检测到烟雾时：
```
==================================================
  🔥 FAN: 50% (MEDIUM) | Conf=0.62 | Area=14.3% | 12.1ms
     模拟动作: GPIO 输出 PWM=50% → 风机变频器
==================================================
  [   120 frames] avg 12.2ms (82.0 FPS)
```

烟雾消失：
```
==================================================
  🛑 FAN STOP  | 无烟雾检测到
==================================================
```

### 6.4 验证通过标准

只要 Jetson 终端能输出上述内容，就证明**模型运行 + 推理计算 + 烟雾判定 + 模拟控制**全链路畅通。后续接真实风机只需替换 `fan_control()` 函数中的汉印语句为 GPIO/Modbus 输出即可。

## 七、模型优化策略

### 7.1 推理加速方案对比

| 方案 | 格式 | 预期 FPS (Orin Nano) | 精度损失 |
|------|------|---------------------|---------|
| PyTorch 直接推理 | .pt | 15-25 FPS | 无 |
| ONNX Runtime | .onnx | 25-40 FPS | 无 |
| TensorRT FP16 | .engine | 60-100 FPS | 极小 (<0.5% mAP) |
| TensorRT INT8 | .engine | 80-120 FPS | 需要校准, ~1-3% mAP |

**推荐**：TensorRT FP16，性能和精度最佳平衡。

### 7.2 其他优化

- **输入分辨率**：640x640 降为 480x480 可再提升 40% FPS
- **批处理**：单帧推理（batch=1）即可满足实时要求
- **NVIDIA DeepStream**：如需多路摄像头，可用 DeepStream 管线（后续阶段）

## 八、硬件连接（后续阶段）

本阶段不涉及真实风机硬件。当前方案通过终端日志模拟风机控制输出：

- "FAN: 50% (MEDIUM)" 代表模拟输出 50% PWM 信号
- "模拟动作: GPIO 输出 PWM=50% → 风机变频器" 是终端日志描述

接入真实风机时，只需将 `fan_control()` 函数中的 `print()` 替换为 GPIO/Modbus 硬件调用即可，模型推理部分无需改动。

## 九、性能预估

| 场景 | 模型格式 | 预估 FPS | 延迟 |
|------|---------|----------|------|
| RTSP 1080p 单路 | TensorRT FP16 | 60-80 FPS | ~15ms |
| RTSP 1080p 单路 | PyTorch | 15-25 FPS | ~50ms |
| 2 路 RTSP | TensorRT FP16 | 30-40 FPS/路 | ~30ms |

## 十、要创建的文件

| 文件 | 路径 | 作用 |
|------|------|------|
| `export_tensorrt.py` | `src/export_tensorrt.py` | PC端导出 TensorRT engine 和 ONNX |
| `smoke_detect.py` | `src/jetson/smoke_detect.py` | Jetson 端唯一脚本：推理 + 浓度判定 + 模拟风机输出 |
| `requirements_jetson.txt` | `requirements_jetson.txt` | Jetson 端依赖清单 |
| `setup_jetson.sh` | `scripts/setup_jetson.sh` | Jetson 一键环境配置脚本 |

## 十一、立即执行步骤

1. 创建 `src/export_tensorrt.py` 并导出 TensorRT engine
2. 创建 `src/jetson/smoke_detect.py`（整合推理+浓度判定+模拟风机）
3. 创建 `requirements_jetson.txt` 和 `scripts/setup_jetson.sh`
4. 将 engine/pt 文件 + 脚本 + 测试视频拷贝到 Jetson
5. 在 Jetson 上运行 `python smoke_detect.py --video test.mp4` 验证
6. 更新 `.gitignore` 忽略 .engine 文件
7. Git 提交 + 推送

## 十二、验证标准

| 步骤 | 验证方法 |
|------|----------|
| TensorRT 导出 | `.engine` 文件生成，大小 ~6MB |
| Jetson 环境 | `python3 -c "import torch; print(torch.cuda.is_available())"` → True |
| 模型加载 | `python smoke_detect.py --video test.mp4` 无报错启动 |
| 推理运行 | 终端每 30 帧输出 avg FPS 统计 |
| 烟雾检测 | 视频中有烟雾时终端打印 `🔥 FAN: XX% (LEVEL)` |
| 模拟风机 | 烟雾出现/消失时终端输出模拟动作日志 |
| 性能达标 | 平均推理 < 30ms（≥30 FPS） |

---

**下一步接续的完整开发方案**见 [项目开发方案文档](../.trae/documents/foundry-smoke-ai-fan-control-plan.md) Phase 3 详细说明。
