import os
import shutil
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
    print(f"PyTorch: {torch.__version__} | CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    config_path = project_root / "data" / "factory_dataset" / "data.yaml"
    if not config_path.exists():
        print(f"Error: Dataset config not found: {config_path}")
        print("Run prepare_dataset.py first after annotation is complete.")
        return

    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    base_model = project_root / "models" / "smoke_detection_best.pt"
    if not base_model.exists():
        print(f"Error: Base model not found: {base_model}")
        return

    print(f"\nLoading base model: {base_model}")
    model = YOLO(str(base_model))

    results = model.train(
        data=str(config_path),
        epochs=50,
        imgsz=640,
        batch=8,
        device=0,
        workers=4,
        optimizer="AdamW",
        lr0=0.0001,
        lrf=0.01,
        cos_lr=True,
        warmup_epochs=2,
        amp=True,
        patience=15,
        save=True,
        save_period=5,
        val=True,
        plots=True,
        project=str(project_root / "runs" / "train"),
        name="factory_finetune",
        exist_ok=True,
    )

    best_weight = project_root / "runs" / "train" / "factory_finetune" / "weights" / "best.pt"
    if best_weight.exists():
        shutil.copy(best_weight, models_dir / "factory_smoke_finetuned.pt")
        print(f"Finetuned model saved to: {models_dir / 'factory_smoke_finetuned.pt'}")

    print("Fine-tuning completed.")


if __name__ == "__main__":
    main()
