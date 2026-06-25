import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from ultralytics import YOLO


@dataclass
class ModelInfo:
    name: str
    path: str
    model_type: str
    num_classes: int
    class_names: list = field(default_factory=list)
    file_size: int = 0
    created_at: str = ""
    status: str = "ready"
    metrics: dict = field(default_factory=dict)


class ModelManager:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.registry_path = self.project_root / "configs" / "model_registry.json"
        self.models_dir = self.project_root / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir = self.project_root / "configs"
        self.configs_dir.mkdir(parents=True, exist_ok=True)
        self._registry = self._load_registry()

    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"models": {}}

    def _save_registry(self):
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, indent=2, ensure_ascii=False)

    def _model_to_info(self, name: str, data: dict) -> ModelInfo:
        return ModelInfo(
            name=name,
            path=data.get("path", ""),
            model_type=data.get("type", "imported"),
            num_classes=data.get("num_classes", 0),
            class_names=data.get("class_names", []),
            file_size=data.get("file_size", 0),
            created_at=data.get("created_at", ""),
            status=data.get("status", "unavailable"),
            metrics=data.get("metrics", {}),
        )

    def validate_model(self, path: Path) -> bool:
        try:
            model = YOLO(str(path))
            _ = model.names
            return True
        except Exception:
            return False

    def get_model_info(self, path: Path) -> Optional[ModelInfo]:
        try:
            model = YOLO(str(path))
            class_names = list(model.names.values()) if model.names else []
            num_classes = len(class_names)
            file_path = Path(path)
            file_size = file_path.stat().st_size if file_path.exists() else 0
            created_at = datetime.fromtimestamp(
                file_path.stat().st_ctime
            ).isoformat() if file_path.exists() else ""
            return ModelInfo(
                name=file_path.stem,
                path=str(file_path),
                model_type="imported",
                num_classes=num_classes,
                class_names=class_names,
                file_size=file_size,
                created_at=created_at,
                status="ready",
                metrics={},
            )
        except Exception:
            return None

    def scan_models_dir(self):
        if not self.models_dir.exists():
            return
        for pt_file in self.models_dir.glob("*.pt"):
            if pt_file.parent == self.project_root and pt_file.name.lower().startswith("yolo"):
                continue
            name = pt_file.stem
            if name in self._registry.get("models", {}):
                continue
            model_path = str(pt_file)
            info = self.get_model_info(pt_file)
            if info is None:
                info = ModelInfo(
                    name=name,
                    path=model_path,
                    model_type="imported",
                    num_classes=0,
                    class_names=[],
                    file_size=pt_file.stat().st_size,
                    created_at=datetime.fromtimestamp(pt_file.stat().st_ctime).isoformat(),
                    status="unavailable",
                    metrics={},
                )
            else:
                info.model_type = "imported"
            self._registry.setdefault("models", {})[name] = {
                "path": info.path,
                "type": info.model_type,
                "num_classes": info.num_classes,
                "class_names": info.class_names,
                "file_size": info.file_size,
                "created_at": info.created_at,
                "status": info.status,
                "metrics": info.metrics,
            }
        self._save_registry()

    def import_model(self, source_path: Path) -> Optional[ModelInfo]:
        source_path = Path(source_path)
        if not source_path.exists() or source_path.suffix.lower() != ".pt":
            return None
        dest_path = self.models_dir / source_path.name
        shutil.copy2(str(source_path), str(dest_path))
        info = self.get_model_info(dest_path)
        if info is None:
            info = ModelInfo(
                name=dest_path.stem,
                path=str(dest_path),
                model_type="imported",
                num_classes=0,
                class_names=[],
                file_size=dest_path.stat().st_size,
                created_at=datetime.fromtimestamp(dest_path.stat().st_ctime).isoformat(),
                status="unavailable",
                metrics={},
            )
        else:
            info.model_type = "imported"
        self._registry.setdefault("models", {})[info.name] = {
            "path": info.path,
            "type": info.model_type,
            "num_classes": info.num_classes,
            "class_names": info.class_names,
            "file_size": info.file_size,
            "created_at": info.created_at,
            "status": info.status,
            "metrics": info.metrics,
        }
        self._save_registry()
        return info

    def download_yolo(self, model_size: str = "n") -> Optional[ModelInfo]:
        valid_sizes = {"n", "s", "m", "l", "x"}
        if model_size not in valid_sizes:
            model_size = "n"
        model_name = f"yolov8{model_size}"
        dest_path = self.models_dir / f"{model_name}.pt"
        if dest_path.exists():
            info = self.get_model_info(dest_path)
            if info:
                info.model_type = "pretrained"
                self._registry.setdefault("models", {})[model_name] = {
                    "path": str(dest_path),
                    "type": "pretrained",
                    "num_classes": info.num_classes,
                    "class_names": info.class_names,
                    "file_size": info.file_size,
                    "created_at": info.created_at,
                    "status": "ready",
                    "metrics": {},
                }
                self._save_registry()
                return info
        try:
            model = YOLO(f"yolov8{model_size}.pt")
            class_names = list(model.names.values()) if model.names else []
            num_classes = len(class_names)
            current_path = Path(f"yolov8{model_size}.pt")
            if current_path.resolve() != dest_path.resolve():
                shutil.move(str(current_path), str(dest_path))
            file_size = dest_path.stat().st_size if dest_path.exists() else 0
            created_at = datetime.fromtimestamp(
                dest_path.stat().st_ctime if dest_path.exists() else time.time()
            ).isoformat()
            info = ModelInfo(
                name=model_name,
                path=str(dest_path),
                model_type="pretrained",
                num_classes=num_classes,
                class_names=class_names,
                file_size=file_size,
                created_at=created_at,
                status="ready",
                metrics={},
            )
            self._registry.setdefault("models", {})[model_name] = {
                "path": str(dest_path),
                "type": "pretrained",
                "num_classes": num_classes,
                "class_names": class_names,
                "file_size": file_size,
                "created_at": created_at,
                "status": "ready",
                "metrics": {},
            }
            self._save_registry()
            return info
        except Exception:
            return None

    def list_models(self) -> list:
        result = []
        for name, data in self._registry.get("models", {}).items():
            result.append(self._model_to_info(name, data))
        return result

    def remove_model(self, name: str) -> bool:
        models = self._registry.get("models", {})
        if name not in models:
            return False
        model_path = Path(models[name].get("path", ""))
        if model_path.exists():
            model_path.unlink()
        del models[name]
        self._save_registry()
        return True

    def compare_models(
        self,
        model_a_path: Path,
        model_b_path: Path,
        test_media_path: Path,
        conf: float = 0.3,
        sample_interval: int = 10,
    ) -> Optional[dict]:
        model_a_path = Path(model_a_path)
        model_b_path = Path(model_b_path)
        test_media_path = Path(test_media_path)

        if not model_a_path.exists() or not model_b_path.exists():
            return None
        if not test_media_path.exists():
            return None

        try:
            model_a = YOLO(str(model_a_path))
            model_b = YOLO(str(model_b_path))
        except Exception:
            return None

        ext = test_media_path.suffix.lower()
        is_image = ext in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

        stats_a = {
            "frames_with_smoke": 0,
            "total_detections": 0,
            "total_conf": 0.0,
            "total_area_pct": 0.0,
            "total_ms": 0.0,
            "samples": 0,
        }
        stats_b = {
            "frames_with_smoke": 0,
            "total_detections": 0,
            "total_conf": 0.0,
            "total_area_pct": 0.0,
            "total_ms": 0.0,
            "samples": 0,
        }

        def collect_stats(model, frame):
            t_start = time.time()
            results = model.predict(frame, conf=conf, verbose=False, device=0)
            ms = (time.time() - t_start) * 1000
            boxes = results[0].boxes
            h, w = frame.shape[:2]
            total_area = w * h

            has_smoke = False
            det_count = 0
            total_conf_val = 0.0
            total_area_val = 0.0

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = results[0].names[cls_id]
                    if "smoke" in cls_name.lower():
                        has_smoke = True
                        conf_val = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        box_area = (x2 - x1) * (y2 - y1)
                        total_conf_val += conf_val
                        total_area_val += (box_area / total_area) * 100
                        det_count += 1

            return {
                "has_smoke": has_smoke,
                "detections": det_count,
                "total_conf": total_conf_val,
                "total_area_pct": total_area_val,
                "inference_ms": ms,
            }

        if is_image:
            frame = cv2.imread(str(test_media_path))
            if frame is None:
                return None

            sa = collect_stats(model_a, frame)
            sb = collect_stats(model_b, frame)

            stats_a["samples"] = 1
            stats_a["total_ms"] = sa["inference_ms"]
            if sa["has_smoke"]:
                stats_a["frames_with_smoke"] = 1
                stats_a["total_detections"] = sa["detections"]
                stats_a["total_conf"] = sa["total_conf"]
                stats_a["total_area_pct"] = sa["total_area_pct"]

            stats_b["samples"] = 1
            stats_b["total_ms"] = sb["inference_ms"]
            if sb["has_smoke"]:
                stats_b["frames_with_smoke"] = 1
                stats_b["total_detections"] = sb["detections"]
                stats_b["total_conf"] = sb["total_conf"]
                stats_b["total_area_pct"] = sb["total_area_pct"]
        else:
            cap = cv2.VideoCapture(str(test_media_path))
            if not cap.isOpened():
                return None

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % sample_interval != 0:
                    frame_idx += 1
                    continue

                sa = collect_stats(model_a, frame)
                stats_a["samples"] += 1
                stats_a["total_ms"] += sa["inference_ms"]
                if sa["has_smoke"]:
                    stats_a["frames_with_smoke"] += 1
                    stats_a["total_detections"] += sa["detections"]
                    stats_a["total_conf"] += sa["total_conf"]
                    stats_a["total_area_pct"] += sa["total_area_pct"]

                sb = collect_stats(model_b, frame)
                stats_b["samples"] += 1
                stats_b["total_ms"] += sb["inference_ms"]
                if sb["has_smoke"]:
                    stats_b["frames_with_smoke"] += 1
                    stats_b["total_detections"] += sb["detections"]
                    stats_b["total_conf"] += sb["total_conf"]
                    stats_b["total_area_pct"] += sb["total_area_pct"]

                frame_idx += 1

            cap.release()

        def safe_div(a, b):
            return a / b if b > 0 else 0.0

        result_a = {
            "model_path": str(model_a_path),
            "model_name": model_a_path.stem,
            "frames_with_smoke": stats_a["frames_with_smoke"],
            "smoke_pct": safe_div(stats_a["frames_with_smoke"], stats_a["samples"]) * 100,
            "total_detections": stats_a["total_detections"],
            "avg_conf": safe_div(stats_a["total_conf"], stats_a["total_detections"]),
            "avg_area_pct": safe_div(stats_a["total_area_pct"], stats_a["total_detections"]),
            "avg_inference_ms": safe_div(stats_a["total_ms"], stats_a["samples"]),
            "samples": stats_a["samples"],
        }

        result_b = {
            "model_path": str(model_b_path),
            "model_name": model_b_path.stem,
            "frames_with_smoke": stats_b["frames_with_smoke"],
            "smoke_pct": safe_div(stats_b["frames_with_smoke"], stats_b["samples"]) * 100,
            "total_detections": stats_b["total_detections"],
            "avg_conf": safe_div(stats_b["total_conf"], stats_b["total_detections"]),
            "avg_area_pct": safe_div(stats_b["total_area_pct"], stats_b["total_detections"]),
            "avg_inference_ms": safe_div(stats_b["total_ms"], stats_b["samples"]),
            "samples": stats_b["samples"],
        }

        return {
            "model_a": result_a,
            "model_b": result_b,
        }
