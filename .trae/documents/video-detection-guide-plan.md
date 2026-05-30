# 工厂烟雾视频检测操作指南 — 实施方案

## 一、目标

针对用户已准备的工厂实际烟雾视频，生成一份清晰的操作指南，回答三个核心问题：
1. 视频文件应该放在哪里
2. 运行后输出结果是什么样
3. 如何检查结果

同时在项目中创建一个 `videos/` 目录用于存放用户的检测视频，并在 `PROJECT_GUIDE.md` 中补充相关说明（可选，如果 PROJECT_GUIDE 已覆盖则跳过）。

---

## 二、当前环境状态（已验证）

| 项目 | 状态 |
|------|------|
| GPU | RTX 5060 Ti, CUDA 可用 |
| 模型 | `models/smoke_detection_best.pt` 已就绪 |
| 依赖 | `venv/Lib/site-packages/` 完整 |
| 启动脚本 | `run.bat` 已可用 |

---

## 三、方案：回答三个核心问题

### 问题 1：视频文件应该放在哪里？

**答案：视频不需要放在项目文件夹内，可以放在任何位置。**

`detect_video.py` 的 `--video` 参数接受**绝对路径**，代码中通过 `cv2.VideoCapture(video_path)` 直接打开文件，与项目目录无关联。

**两种推荐做法：**

| 方式 | 路径示例 | 适用场景 |
|------|---------|----------|
| 直接指定原始路径 | `E:\videos\factory_smoke.mp4` | 视频已在某处，不想移动 |
| 在项目内创建 `videos/` 目录 | `videos\factory_smoke.mp4` | 方便管理，视频和代码在一起 |

创建 `videos/` 目录的命令：
```powershell
mkdir "e:\project\Dusc AI CV GPU\videos"
```

然后将视频文件放入该目录即可。

---

### 问题 2：运行后输出结果是什么样？

**答案：输出是「带标注的 MP4 视频文件」+「控制台日志」两种。**

#### 2.1 带标注的视频

| 项目 | 说明 |
|------|------|
| **输出路径** | `runs/detect/video_result/output.mp4` |
| **格式** | MP4 (mp4v 编码) |
| **分辨率** | 与输入视频相同 |
| **帧率** | 与输入视频相同 |
| **叠加信息** | 检测边界框 + 类别标签(fire/smoke) + 置信度 + 实时 FPS |

视频中，每一帧上会绘制：
- 检测到的 smoke 目标：**红色**边界框，标签如 `smoke 0.85`
- 检测到的 fire 目标：**橙色**边界框，标签如 `fire 0.92`
- 左上角：绿色 FPS 信息 `FPS: 385.0`

#### 2.2 控制台日志

运行时终端会输出：
```
Video: 1920x1080, 30.0 FPS, 1800 frames
Processed 100/1800 frames, avg inference: 2.6ms (384.6 FPS)
Processed 200/1800 frames, avg inference: 2.5ms (400.0 FPS)
...
Processing completed:
  Total frames: 1800
  Average inference time: 2.6ms
  Average FPS: 384.6
  Output saved to: E:\project\Dusc AI CV GPU\runs\detect\video_result\output.mp4
```

> **注意**：当前版本不输出 JSON/CSV 结构化数据。如需每帧的检测数据（类别、坐标、置信度），需在代码中扩展输出逻辑。

---

### 问题 3：如何检查结果？

**答案：用视频播放器打开输出视频，或使用 `--show` 实时观看。**

#### 方式 A：事后检查（推荐）
运行完成后，用任意视频播放器打开：
```
runs\detect\video_result\output.mp4
```
支持的播放器：VLC、Windows Media Player、PotPlayer 等。

#### 方式 B：实时观看
运行时加 `--show` 参数，会弹出 OpenCV 窗口实时显示检测过程：
```batch
run.bat src\detect_video.py --video videos\factory_smoke.mp4 --show
```
按 `q` 键可提前终止。

#### 方式 C：同时实时观看 + 保存
默认行为就是保存，加上 `--show` 即可两者兼得：
```batch
run.bat src\detect_video.py --video videos\factory_smoke.mp4 --show
```

---

## 四、完整操作步骤

### 步骤 1：准备视频
```powershell
mkdir "e:\project\Dusc AI CV GPU\videos"
copy 你的视频文件.mp4 "e:\project\Dusc AI CV GPU\videos\"
```

### 步骤 2：运行检测
```batch
cd "e:\project\Dusc AI CV GPU"
run.bat src\detect_video.py --video videos\你的视频文件.mp4
```

**推荐参数（提高检测精度 + 实时显示）：**
```batch
run.bat src\detect_video.py --video videos\你的视频文件.mp4 --conf 0.4 --show
```

参数说明：
| 参数 | 值 | 作用 |
|------|-----|------|
| `--conf 0.4` | 提高阈值 | 减少误检，只显示置信度 > 40% 的目标 |
| `--show` | 实时窗口 | 弹出窗口实时观看检测过程 |
| `--no-save` | 不保存 | 只看不保存（可选） |

### 步骤 3：查看结果
```powershell
start runs\detect\video_result\output.mp4
```

---

## 五、不创建新文件

本方案**不涉及修改任何现有代码文件**，只产出：
1. 本方案文档（`.trae/documents/video-detection-guide-plan.md`）
2. 项目内创建 `videos/` 空目录（方便用户使用）
3. 更新 `.gitignore` 忽略 `videos/` 目录

> 现有的 `PROJECT_GUIDE.md` 已经包含了完整的视频检测使用指南（第204-262行），无需额外修改。

---

## 六、验证标准

| 步骤 | 验证方法 |
|------|----------|
| 环境就绪 | `run.bat` 可正常执行（模型、依赖、GPU 均就绪） |
| 视频检测运行 | 用户按指南操作后，终端无报错，能看到进度输出 |
| 结果文件生成 | `runs/detect/video_result/output.mp4` 文件存在且大小 > 0 |
| 检测结果可查看 | 用视频播放器打开 output.mp4 能看到检测框叠加 |
