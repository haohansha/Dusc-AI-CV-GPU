import json
import random
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2


@dataclass
class MediaInfo:
    name: str
    path: str
    media_type: str
    duration: float
    resolution: str
    fps: float
    frame_count: int
    file_size: int
    imported_at: datetime
    has_labels: bool


class DatasetManager:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.registry_path = self.project_root / "configs" / "media_registry.json"
        self._registry = {"media": {}}
        self._load_registry()

    def _load_registry(self):
        if self.registry_path.exists():
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self._registry = json.load(f)
        else:
            self._registry = {"media": {}}

    def _save_registry(self):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, indent=2, ensure_ascii=False, default=str)

    def scan_media_dir(self):
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            return []

        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

        new_entries = []

        for file_path in data_dir.rglob("*"):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if suffix not in video_extensions and suffix not in image_extensions:
                continue

            relative_path = str(file_path.relative_to(self.project_root)).replace("\\", "/")
            name = file_path.name

            if name in self._registry.get("media", {}):
                continue

            media_type = "video" if suffix in video_extensions else "image"
            file_size = file_path.stat().st_size

            entry = {
                "path": relative_path,
                "type": media_type,
                "duration": 0.0,
                "resolution": "",
                "fps": 0.0,
                "frame_count": 0,
                "file_size": file_size,
                "imported_at": datetime.now().isoformat(),
                "has_labels": False,
            }

            if media_type == "video":
                cap = cv2.VideoCapture(str(file_path))
                if cap.isOpened():
                    entry["fps"] = round(cap.get(cv2.CAP_PROP_FPS), 2)
                    entry["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    entry["resolution"] = f"{w}x{h}"
                    if entry["fps"] > 0:
                        entry["duration"] = round(entry["frame_count"] / entry["fps"], 2)
                    cap.release()

            self._registry.setdefault("media", {})[name] = entry
            new_entries.append(self._entry_to_mediainfo(name, entry))

        self._save_registry()
        return new_entries

    def import_video(self, source_path) -> MediaInfo:
        source_path = Path(source_path)
        dest_dir = self.project_root / "data" / "media"
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = dest_dir / source_path.name
        shutil.copy2(str(source_path), str(dest_path))

        cap = cv2.VideoCapture(str(dest_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {dest_path}")

        fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        resolution = f"{w}x{h}"
        duration = round(frame_count / fps, 2) if fps > 0 else 0.0
        cap.release()

        relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
        file_size = dest_path.stat().st_size
        imported_at = datetime.now()

        entry = {
            "path": relative_path,
            "type": "video",
            "duration": duration,
            "resolution": resolution,
            "fps": fps,
            "frame_count": frame_count,
            "file_size": file_size,
            "imported_at": imported_at.isoformat(),
            "has_labels": False,
        }

        name = source_path.name
        self._registry.setdefault("media", {})[name] = entry
        self._save_registry()

        return self._entry_to_mediainfo(name, entry)

    def import_images(self, source_paths) -> list:
        dest_dir = self.project_root / "data" / "media" / "images"
        dest_dir.mkdir(parents=True, exist_ok=True)

        results = []

        for sp in source_paths:
            sp = Path(sp)
            dest_path = dest_dir / sp.name
            shutil.copy2(str(sp), str(dest_path))

            relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
            file_size = dest_path.stat().st_size
            imported_at = datetime.now()

            entry = {
                "path": relative_path,
                "type": "image",
                "duration": 0.0,
                "resolution": "",
                "fps": 0.0,
                "frame_count": 1,
                "file_size": file_size,
                "imported_at": imported_at.isoformat(),
                "has_labels": False,
            }

            name = sp.name
            self._registry.setdefault("media", {})[name] = entry
            results.append(self._entry_to_mediainfo(name, entry))

        self._save_registry()
        return results

    def extract_frames(self, video_path, interval=15, output_dir=None, max_frames=None):
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_dir is None:
            output_dir = self.project_root / "data" / "factory_frames"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        video_name = video_path.stem

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        extracted = 0
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % interval == 0:
                filename = f"{video_name}_frame_{frame_idx:06d}.jpg"
                output_path = output_dir / filename
                cv2.imwrite(str(output_path), frame)
                extracted += 1

            frame_idx += 1

            if max_frames and extracted >= max_frames:
                break

        cap.release()
        return extracted

    def prepare_dataset(self, frames_dir, original_dataset_dir=None, output_dir=None, val_split=0.2):
        frames_dir = Path(frames_dir)
        if output_dir is None:
            output_dir = self.project_root / "data" / "factory_dataset"
        else:
            output_dir = Path(output_dir)

        ann_files = sorted(frames_dir.glob("*.txt"))
        paired = []
        for ann_file in ann_files:
            for ext in (".jpg", ".jpeg", ".png"):
                img_file = frames_dir / (ann_file.stem + ext)
                if img_file.exists():
                    paired.append((img_file, ann_file))
                    break

        if not paired:
            return None

        random.seed(42)
        random.shuffle(paired)
        n_val = max(1, int(len(paired) * val_split))
        train_pairs = paired[n_val:]
        val_pairs = paired[:n_val]

        train_img_dir = output_dir / "train" / "images"
        train_lbl_dir = output_dir / "train" / "labels"
        val_img_dir = output_dir / "val" / "images"
        val_lbl_dir = output_dir / "val" / "labels"

        for d in [train_img_dir, train_lbl_dir, val_img_dir, val_lbl_dir]:
            d.mkdir(parents=True, exist_ok=True)

        for img, lbl in train_pairs:
            shutil.copy2(str(img), str(train_img_dir / img.name))
            shutil.copy2(str(lbl), str(train_lbl_dir / lbl.name))
        for img, lbl in val_pairs:
            shutil.copy2(str(img), str(val_img_dir / img.name))
            shutil.copy2(str(lbl), str(val_lbl_dir / lbl.name))

        if original_dataset_dir is not None:
            original_dataset_dir = Path(original_dataset_dir)
            orig_train_img = original_dataset_dir / "train" / "images"
            orig_train_lbl = original_dataset_dir / "train" / "labels"

            if orig_train_img.exists() and orig_train_lbl.exists():
                orig_imgs = sorted(orig_train_img.glob("*.jpg"))
                for img in orig_imgs:
                    lbl = orig_train_lbl / (img.stem + ".txt")
                    if lbl.exists():
                        with open(lbl, "r") as f:
                            new_lines = []
                            for line in f:
                                parts = line.strip().split()
                                if not parts:
                                    continue
                                cls_id = int(parts[0])
                                if cls_id == 2:
                                    new_lines.append(f"0 {' '.join(parts[1:])}\n")
                        if new_lines:
                            shutil.copy2(str(img), str(train_img_dir / img.name))
                            with open(train_lbl_dir / lbl.name, "w") as fw:
                                fw.writelines(new_lines)

        data_yaml = output_dir / "data.yaml"
        data_yaml.write_text(
            f"path: {output_dir.as_posix()}\n"
            "train: train/images\n"
            "val: val/images\n\n"
            "nc: 1\n"
            "names:\n"
            "  0: smoke\n",
            encoding="utf-8",
        )

        total_train_img = len(list(train_img_dir.glob("*")))
        total_train_lbl = len(list(train_lbl_dir.glob("*")))
        total_val_img = len(list(val_img_dir.glob("*")))
        total_val_lbl = len(list(val_lbl_dir.glob("*")))

        return {
            "total_paired": len(paired),
            "train_images": total_train_img,
            "train_labels": total_train_lbl,
            "val_images": total_val_img,
            "val_labels": total_val_lbl,
            "output_dir": str(output_dir),
        }

    def get_dataset_summary(self, dataset_path=None):
        if dataset_path is None:
            dataset_path = self.project_root / "data" / "smoke_dataset"
        dataset_path = Path(dataset_path)

        train_img_dir = dataset_path / "train" / "images"
        val_img_dir = dataset_path / "val" / "images"

        train_count = len(list(train_img_dir.glob("*"))) if train_img_dir.exists() else 0
        val_count = len(list(val_img_dir.glob("*"))) if val_img_dir.exists() else 0
        total_images = train_count + val_count

        data_yaml_path = dataset_path / "data.yaml"
        classes = []
        nc = 0
        if data_yaml_path.exists():
            import yaml
            with open(data_yaml_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
            names = yaml_data.get("names", {})
            if isinstance(names, dict):
                classes = list(names.values())
            elif isinstance(names, list):
                classes = names
            nc = yaml_data.get("nc", len(classes))

        split_info = {}
        if total_images > 0:
            split_info["train_ratio"] = round(train_count / total_images, 3) if total_images > 0 else 0
            split_info["val_ratio"] = round(val_count / total_images, 3) if total_images > 0 else 0

        return {
            "total_images": total_images,
            "train_count": train_count,
            "val_count": val_count,
            "classes": classes,
            "nc": nc,
            "split_info": split_info,
        }

    def list_media(self):
        return [self._entry_to_mediainfo(name, entry) for name, entry in self._registry.get("media", {}).items()]

    def remove_media(self, name, delete_file=False):
        media = self._registry.get("media", {})
        if name not in media:
            return False

        entry = media[name]

        if delete_file:
            file_path = self.project_root / entry["path"]
            if file_path.exists():
                file_path.unlink()

        del media[name]
        self._save_registry()
        return True

    def _entry_to_mediainfo(self, name, entry):
        return MediaInfo(
            name=name,
            path=entry["path"],
            media_type=entry["type"],
            duration=entry.get("duration", 0.0),
            resolution=entry.get("resolution", ""),
            fps=entry.get("fps", 0.0),
            frame_count=entry.get("frame_count", 0),
            file_size=entry.get("file_size", 0),
            imported_at=datetime.fromisoformat(entry["imported_at"]) if isinstance(entry["imported_at"], str) else entry["imported_at"],
            has_labels=entry.get("has_labels", False),
        )
