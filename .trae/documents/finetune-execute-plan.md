# 工厂标注数据微调 + 演示 —— 实施方案

## 一、目标

使用 `data/factory_frames/` 中已完成的 smoke 标注数据，执行模型微调完整流程，并用第三段视频 `videos/VID_20230501_160954.mp4` 演示微调前后效果对比。

## 二、当前状态

| 项目 | 状态 |
|------|------|
| 标注数据 | ✅ `data/factory_frames/` 含 smoke 标注 .txt 文件 |
| 抽帧脚本 | ✅ `src/extract_frames.py` |
| 数据整合脚本 | ✅ `src/prepare_dataset.py` |
| 微调训练脚本 | ✅ `src/train_finetune.py` |
| 对比评估脚本 | ✅ `src/compare_models.py` |
| 基础模型 | ✅ `models/smoke_detection_best.pt` |
| 新视频 | ✅ `videos/VID_20230501_160954.mp4` |

## 三、执行步骤

### Step 1: 对第三段视频抽帧

```batch
run.bat src\extract_frames.py --video videos\VID_20230501_160954.mp4 --interval 15 --output data\factory_frames
```

将新视频的帧也加入 `factory_frames/`，后续对比时覆盖更全面。

### Step 2: 数据整合

```batch
run.bat src\prepare_dataset.py
```

整合工厂标注帧 + 原有公开数据集，生成 `data/factory_dataset/`。

### Step 3: 微调训练

```batch
run.bat src\train_finetune.py
```

基于 `models/smoke_detection_best.pt` 继续训练，lr=0.0001，50 epochs，自动保存 best.pt。

### Step 4: 对比评估

```batch
run.bat src\compare_models.py --video videos\VID_20230501_160954.mp4
```

用新旧模型对第三段视频做推理对比，输出检测帧数、置信度、检测框面积占比等指标。

### Step 5: Git 提交

提交微调结果和评估日志。

## 四、不修改的文件

所有现有脚本和配置文件均无需修改，直接按现有脚本执行即可。

## 五、验证标准

| 步骤 | 验证方法 |
|------|----------|
| 视频抽帧 | 新帧成功写入 `factory_frames/` |
| 数据整合 | `factory_dataset/data.yaml` 生成，train/val 目录有图片和标注 |
| 微调训练 | 终端无报错，`models/factory_smoke_finetuned.pt` 生成 |
| 对比评估 | 输出新旧模型对比表格，新模型指标 ≥ 旧模型 |
