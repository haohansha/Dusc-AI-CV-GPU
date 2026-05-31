# 第二轮微调 + 后半段视频验证 — 实施方案

## 一、当前状态

| 项目 | 状态 |
|------|------|
| 新增标注 | ✅ 63 个新 XML 标注（30s视频抽帧），需转 YOLO |
| 已有YOLO标注 | 141 个 TXT |
| 总标注 | 204 帧含标注 |
| 前30s视频 | `videos/VID_20230501_160954_30s.mp4` (847帧) |
| 完整视频 | `videos/VID_20230501_160954.mp4` (1818帧, 64.4s) |

## 二、执行步骤

### Step 1: XML → YOLO 转换

用 Python 脚本将新增的 63 个 XML 标注转为 YOLO TXT 格式。

### Step 2: 数据整合

```batch
run.bat src\prepare_dataset.py
```

重新整合全部 204 帧标注 + 原数据集，生成新 `data/factory_dataset/`。

### Step 3: 微调训练

```batch
run.bat src\train_finetune.py
```

基于上次微调的 `models/factory_smoke_finetuned.pt` 继续训练。

### Step 4: 提取视频后半段（30s后）

从 `VID_20230501_160954.mp4` 第 847 帧开始到结尾，输出 `videos/VID_20230501_160954_after30s.mp4`。

### Step 5: 对后半段视频推理

用新一轮微调模型对后半段视频推理，输出带标注视频到 `runs/detect/video_result/output.mp4`。

## 三、不修改的文件

全部使用现有脚本，无需新建或修改代码。

## 四、验证标准

| 步骤 | 验证 |
|------|------|
| XML转换 | 所有 XML 有对应 TXT |
| 数据整合 | train/val 数据量增加 |
| 微调训练 | 正常收敛，best.pt 生成 |
| 后半段视频 | 847帧后内容正确 |
| 结果视频 | output.mp4 含 smoke 检测框 |
