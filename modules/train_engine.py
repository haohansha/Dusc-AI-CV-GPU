import csv
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import torch
from ultralytics import YOLO


@dataclass
class TrainingConfig:
    data: str = ""
    model: str = ""
    epochs: int = 50
    imgsz: int = 640
    batch: int = 8
    device: int = 0
    workers: int = 4
    optimizer: str = "AdamW"
    lr0: float = 0.0001
    lrf: float = 0.01
    momentum: float = 0.937
    weight_decay: float = 0.0005
    warmup_epochs: int = 2
    warmup_momentum: float = 0.8
    cos_lr: bool = True
    amp: bool = True
    patience: int = 15
    save_period: int = 5
    project: str = "runs/train"
    name: str = "training"
    exist_ok: bool = True
    pretrained: bool = True
    resume: bool = False


class TrainEngine:
    def __init__(self, project_root: Path):
        self._project_root = project_root
        self._runtime_status = "idle"
        self._current_epoch = 0
        self._total_epochs = 0
        self._stop_flag = False

        os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
        os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

    def train(self, config: TrainingConfig, progress_callback: Optional[Callable] = None) -> Path:
        self._runtime_status = "training"
        self._stop_flag = False
        self._current_epoch = 0
        self._total_epochs = config.epochs

        models_dir = self._project_root / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        model = YOLO(config.model)

        model.train(
            data=config.data,
            epochs=config.epochs,
            imgsz=config.imgsz,
            batch=config.batch,
            device=config.device,
            workers=config.workers,
            optimizer=config.optimizer,
            lr0=config.lr0,
            lrf=config.lrf,
            momentum=config.momentum,
            weight_decay=config.weight_decay,
            warmup_epochs=config.warmup_epochs,
            warmup_momentum=config.warmup_momentum,
            cos_lr=config.cos_lr,
            amp=config.amp,
            patience=config.patience,
            save_period=config.save_period,
            project=config.project,
            name=config.name,
            exist_ok=config.exist_ok,
            pretrained=config.pretrained,
            resume=config.resume,
            save=True,
            val=True,
            plots=True,
        )

        self._current_epoch = config.epochs

        metrics = self._read_metrics(config.project, config.name)

        best_weight = Path(config.project) / config.name / "weights" / "best.pt"
        best_model_path = models_dir / f"{config.name}_best.pt"

        if best_weight.exists():
            shutil.copy(best_weight, best_model_path)

        if progress_callback:
            progress_callback(config.epochs, config.epochs, metrics)

        if self._stop_flag:
            self._runtime_status = "stopped"
        else:
            self._runtime_status = "idle"

        return best_weight

    def stop(self):
        self._stop_flag = True
        self._runtime_status = "stopped"

    def get_status(self) -> dict:
        return {
            "status": self._runtime_status,
            "current_epoch": self._current_epoch,
            "total_epochs": self._total_epochs,
        }

    def get_default_config(self) -> TrainingConfig:
        config = TrainingConfig()
        config.data = str(self._project_root / "data" / "factory_dataset" / "data.yaml")

        factory_model = self._project_root / "models" / "factory_smoke_finetuned.pt"
        if factory_model.exists():
            config.model = str(factory_model)
        else:
            base_model = self._project_root / "models" / "smoke_detection_best.pt"
            if base_model.exists():
                config.model = str(base_model)

        config.project = str(self._project_root / "runs" / "train")
        config.name = "factory_finetune"
        return config

    def _read_metrics(self, project: str, name: str) -> dict:
        results_csv = Path(project) / name / "results.csv"
        if not results_csv.exists():
            return {}

        with open(results_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return {}

        last_row = rows[-1]
        metrics = {}
        for key, value in last_row.items():
            clean_key = key.strip()
            try:
                metrics[clean_key] = float(value)
            except (ValueError, TypeError):
                metrics[clean_key] = value

        return metrics
