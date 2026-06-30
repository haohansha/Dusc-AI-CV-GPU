import json
from pathlib import Path


class AppConfig:
    DEFAULTS = {
        "default_model_dir": "models",
        "default_data_dir": "data/media",
        "default_output_dir": "runs",
        "theme": "light",
        "language": "zh_CN",
        "last_model": "",
        "window_geometry": "",
        "jetson": {
            "tensorrt_version": "10.3.0",
            "ultralytics_version": "8.3.252",
            "opencv_version": "4.11.0",
            "imgsz": 640,
            "half": True,
            "device": 0,
            "workspace": 4,
            "precision": "FP16",
            "camera_type": "csi",
            "camera_index": 0,
            "camera_pipeline": "",
        },
    }

    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "configs" / "app_config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def reset(self):
        self._data = dict(self.DEFAULTS)
        self.save()
