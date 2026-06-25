import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
venv_path = str(project_root / "venv" / "Lib" / "site-packages")
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import os
os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

from modules.train_engine import TrainingConfig, TrainEngine


def main():
    train_engine = TrainEngine(project_root)

    config = TrainingConfig(
        data=str(project_root / "data" / "smoke_dataset" / "smoke_data.yaml"),
        model="yolov8n.pt",
        epochs=100,
        imgsz=640,
        batch=8,
        device=0,
        workers=4,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        cos_lr=True,
        amp=True,
        patience=20,
        save_period=10,
        project=str(project_root / "runs" / "train"),
        name="smoke_detection",
        exist_ok=True,
        pretrained=True,
        resume=False,
    )

    train_engine.train(config)


if __name__ == "__main__":
    main()
