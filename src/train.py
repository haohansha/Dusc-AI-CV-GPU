import os
import sys
from pathlib import Path


project_root = Path(__file__).parent.parent
venv_path = str(project_root / "venv" / "Lib" / "site-packages")
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

import torch
from ultralytics import YOLO


def main():
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    config_path = project_root / "data" / "smoke_dataset" / "smoke_data.yaml"
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDataset config: {config_path}")
    print(f"Starting smoke detection training...")

    model = YOLO("yolov8n.pt")

    results = model.train(
        data=str(config_path),
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
        project=str(project_root / "runs" / "train"),
        name="smoke_detection",
        exist_ok=True,
        pretrained=True,
        resume=False,
        amp=True,
        patience=20,
        save=True,
        save_period=10,
        val=True,
        plots=True,
    )

    best_weight = project_root / "runs" / "train" / "smoke_detection" / "weights" / "best.pt"
    if best_weight.exists():
        import shutil
        shutil.copy(best_weight, models_dir / "smoke_detection_best.pt")
        print(f"Best model saved to: {models_dir / 'smoke_detection_best.pt'}")

    print(f"Training completed.")


if __name__ == "__main__":
    main()
