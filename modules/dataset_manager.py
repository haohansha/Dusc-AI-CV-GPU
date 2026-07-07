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
    categories: list = None  # 素材分类归属，如 ["微调用", "测试用"]

    def __post_init__(self):
        if self.categories is None:
            self.categories = []


@dataclass
class LabelInfo:
    name: str           # 文件名，如 "smoke_01.txt"
    path: str           # 相对路径，如 "data/media/labels/smoke_01.txt"
    file_size: int
    line_count: int     # 标注行数（一个标注框一行）
    imported_at: datetime


class DatasetManager:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.registry_path = self.project_root / "configs" / "media_registry.json"
        # 统一资源目录：所有导入的视频/图片/标签及抽帧产物均存放于此
        self.resource_dir = self.project_root / "resource"
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

    def scan_media_dir(self, target_dir=None, copy_files=True):
        """扫描文件夹，导入所有视频/图片/标签文件

        Args:
            target_dir: 要扫描的目录，默认为 project_root/data
            copy_files: True=复制到项目内 data/media/ 下并登记；
                        False=仅登记原路径不复制

        Returns:
            dict: {"videos": [MediaInfo...], "images": [MediaInfo...], "labels": [LabelInfo...]}
        """
        if target_dir is not None:
            data_dir = Path(target_dir)
        else:
            data_dir = self.project_root / "data"
        if not data_dir.exists():
            return {"videos": [], "images": [], "labels": []}

        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

        new_videos = []
        new_images = []
        new_labels = []

        for file_path in data_dir.rglob("*"):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()

            if suffix in video_extensions:
                media_type = "video"
            elif suffix in image_extensions:
                media_type = "image"
            elif suffix == ".txt":
                media_type = "label"
            else:
                continue

            name = file_path.name

            # 已存在则跳过
            if media_type != "label" and name in self._registry.get("media", {}):
                continue
            if media_type == "label" and name in self._registry.get("labels", {}):
                continue

            # 决定文件最终路径：复制 or 原地
            actual_path = file_path
            if copy_files:
                if media_type == "video":
                    dest_dir = self.resource_dir / "videos"
                elif media_type == "image":
                    dest_dir = self.resource_dir / "images"
                else:  # label
                    dest_dir = self.resource_dir / "labels"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / name
                # 避免复制到自身
                if file_path.resolve() != dest_path.resolve():
                    shutil.copy2(str(file_path), str(dest_path))
                    actual_path = dest_path

            try:
                stored_path = str(actual_path.relative_to(self.project_root)).replace("\\", "/")
            except ValueError:
                # 文件在项目外，存绝对路径
                stored_path = str(actual_path).replace("\\", "/")

            file_size = actual_path.stat().st_size
            imported_at = datetime.now().isoformat()

            if media_type == "label":
                line_count = 0
                try:
                    with open(actual_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                line_count += 1
                except Exception:
                    line_count = 0
                entry = {
                    "path": stored_path,
                    "file_size": file_size,
                    "line_count": line_count,
                    "imported_at": imported_at,
                }
                self._registry.setdefault("labels", {})[name] = entry
                new_labels.append(LabelInfo(
                    name=name, path=stored_path,
                    file_size=file_size, line_count=line_count,
                    imported_at=datetime.now(),
                ))
            else:
                entry = {
                    "path": stored_path,
                    "type": media_type,
                    "duration": 0.0,
                    "resolution": "",
                    "fps": 0.0,
                    "frame_count": 0,
                    "file_size": file_size,
                    "imported_at": imported_at,
                    "has_labels": False,
                }
                if media_type == "video":
                    cap = cv2.VideoCapture(str(actual_path))
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
                mi = self._entry_to_mediainfo(name, entry)
                if media_type == "video":
                    new_videos.append(mi)
                else:
                    new_images.append(mi)

        self._save_registry()
        return {"videos": new_videos, "images": new_images, "labels": new_labels}

    def import_video(self, source_path) -> MediaInfo:
        source_path = Path(source_path)
        dest_dir = self.resource_dir / "videos"
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
        dest_dir = self.resource_dir / "images"
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

    def import_labels(self, source_paths) -> list:
        """导入 YOLO 标签文件（.txt）到 resource/labels/"""
        dest_dir = self.resource_dir / "labels"
        dest_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for sp in source_paths:
            sp = Path(sp)
            if sp.suffix.lower() != ".txt":
                continue
            dest_path = dest_dir / sp.name
            shutil.copy2(str(sp), str(dest_path))
            relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
            # 统计非空行数（标注框数）
            line_count = 0
            try:
                with open(dest_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            line_count += 1
            except Exception:
                line_count = 0
            entry = {
                "path": relative_path,
                "file_size": dest_path.stat().st_size,
                "line_count": line_count,
                "imported_at": datetime.now().isoformat(),
            }
            name = sp.name
            self._registry.setdefault("labels", {})[name] = entry
            results.append(LabelInfo(
                name=name, path=relative_path,
                file_size=entry["file_size"], line_count=line_count,
                imported_at=datetime.now(),
            ))
        self._save_registry()
        return results

    def save_label_for_image(self, image_name, boxes):
        """保存图片的标签到 resource/labels/<stem>.txt

        当 boxes 为空时，删除对应的 .txt 文件并从 registry 移除（表示该图片无标注）。

        Args:
            image_name: 图片文件名，如 "smoke_01.jpg"
            boxes: list of (class_id, xc, yc, w, h) 归一化坐标
        Returns:
            LabelInfo 或 None（删除时返回 None）
        """
        stem = Path(image_name).stem
        dest_dir = self.resource_dir / "labels"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{stem}.txt"
        name = f"{stem}.txt"

        # 标签为空 → 删除文件 + 从 registry 移除
        if not boxes:
            if dest_path.exists():
                dest_path.unlink()
            self._registry.get("labels", {}).pop(name, None)
            self._save_registry()
            return None

        # 写入 YOLO 格式
        with open(dest_path, "w", encoding="utf-8") as f:
            for cid, xc, yc, w, h in boxes:
                f.write(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")

        relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
        line_count = len(boxes)
        entry = {
            "path": relative_path,
            "file_size": dest_path.stat().st_size,
            "line_count": line_count,
            "imported_at": datetime.now().isoformat(),
        }
        self._registry.setdefault("labels", {})[name] = entry
        self._save_registry()
        return LabelInfo(
            name=name, path=relative_path,
            file_size=entry["file_size"], line_count=line_count,
            imported_at=datetime.now(),
        )

    def extract_frames(self, video_path, interval=15, output_dir=None, max_frames=None):
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_dir is None:
            output_dir = self.resource_dir / "images"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        video_name = video_path.stem

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        extracted = 0
        frame_idx = 0
        generated_paths = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % interval == 0:
                filename = f"{video_name}_frame_{frame_idx:06d}.jpg"
                output_path = output_dir / filename
                cv2.imwrite(str(output_path), frame)
                generated_paths.append(output_path)
                extracted += 1

            frame_idx += 1

            if max_frames and extracted >= max_frames:
                break

        cap.release()

        # 自动注册抽帧生成的图片到 registry（跳过已登记的）
        media = self._registry.setdefault("media", {})
        new_count = 0
        for img_path in generated_paths:
            name = img_path.name
            if name in media:
                continue
            relative_path = str(img_path.relative_to(self.project_root)).replace("\\", "/")
            entry = {
                "path": relative_path,
                "type": "image",
                "duration": 0.0,
                "resolution": "",
                "fps": 0.0,
                "frame_count": 1,
                "file_size": img_path.stat().st_size,
                "imported_at": datetime.now().isoformat(),
                "has_labels": False,
            }
            media[name] = entry
            new_count += 1
        if new_count > 0:
            self._save_registry()

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
            raw_path = entry["path"]
            p = Path(raw_path)
            file_path = p if p.is_absolute() else self.project_root / p
            if file_path.exists():
                file_path.unlink()

        del media[name]
        self._save_registry()
        return True

    def list_labels(self):
        labels = self._registry.get("labels", {})
        result = []
        for name, entry in labels.items():
            result.append(LabelInfo(
                name=name,
                path=entry["path"],
                file_size=entry.get("file_size", 0),
                line_count=entry.get("line_count", 0),
                imported_at=datetime.fromisoformat(entry["imported_at"]) if isinstance(entry["imported_at"], str) else entry["imported_at"],
            ))
        return result

    def remove_label(self, name, delete_file=False):
        labels = self._registry.get("labels", {})
        if name not in labels:
            return False
        entry = labels[name]
        if delete_file:
            raw_path = entry["path"]
            p = Path(raw_path)
            file_path = p if p.is_absolute() else self.project_root / p
            if file_path.exists():
                file_path.unlink()
        del labels[name]
        self._save_registry()
        return True

    def has_label_for(self, image_name):
        """检查图片是否有对应标签（按 stem 匹配，如 smoke_01.jpg ↔ smoke_01.txt）"""
        image_stem = Path(image_name).stem
        labels = self._registry.get("labels", {})
        return any(Path(name).stem == image_stem for name in labels.keys())

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
            categories=entry.get("categories", []),
        )

    # ---------- 素材分类管理 ----------

    def list_categories(self):
        """返回所有分类名列表"""
        return list(self._registry.get("categories", []))

    def add_category(self, name):
        """新建分类，重名则忽略"""
        cats = self._registry.setdefault("categories", [])
        if name not in cats:
            cats.append(name)
            self._save_registry()

    def rename_category(self, old_name, new_name):
        """重命名分类，同步更新所有素材的 categories 字段"""
        cats = self._registry.get("categories", [])
        if old_name not in cats:
            return
        idx = cats.index(old_name)
        cats[idx] = new_name
        for entry in self._registry.get("media", {}).values():
            if old_name in entry.get("categories", []):
                entry["categories"] = [new_name if c == old_name else c
                                       for c in entry["categories"]]
        self._save_registry()

    def delete_category(self, name):
        """删除分类，同步从所有素材移除"""
        cats = self._registry.get("categories", [])
        if name in cats:
            cats.remove(name)
        for entry in self._registry.get("media", {}).values():
            if name in entry.get("categories", []):
                entry["categories"].remove(name)
        self._save_registry()

    def set_media_categories(self, media_name, categories):
        """设置单个素材的分类列表（覆盖式）"""
        entry = self._registry.get("media", {}).get(media_name)
        if entry is None:
            return
        entry["categories"] = list(categories)
        self._save_registry()

    def list_media_by_category(self, category):
        """返回属于指定分类的所有 MediaInfo"""
        return [m for m in self.list_media() if category in m.categories]
