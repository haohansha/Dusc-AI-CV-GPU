import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ultralytics import YOLO


@dataclass
class ExportConfig:
    format: str = "engine"
    imgsz: int = 640
    half: bool = True
    int8: bool = False
    workspace: int = 4
    simplify: bool = True
    device: int = 0
    model_path: str = ""


class ExportEngine:

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    def export_tensorrt(
        self,
        model_path: str,
        config: Optional[ExportConfig] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Optional[Path]:
        if config is None:
            config = ExportConfig()

        model_abs_path = str(self.project_root / model_path)
        model_stem = Path(model_abs_path).stem
        output_path = self.project_root / "models" / f"{model_stem}.engine"

        if progress_callback:
            progress_callback(10, "Loading model for TensorRT export...")

        model = YOLO(model_abs_path)

        if progress_callback:
            progress_callback(30, "Exporting to TensorRT .engine format...")

        try:
            model.export(
                format="engine",
                imgsz=config.imgsz,
                half=config.half,
                int8=config.int8,
                device=config.device,
                workspace=config.workspace,
                simplify=config.simplify,
            )
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"TensorRT export failed: {e}")
            return None

        if progress_callback:
            progress_callback(100, f"TensorRT export complete: {output_path}")

        return output_path

    def export_onnx(
        self,
        model_path: str,
        config: Optional[ExportConfig] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Optional[Path]:
        if config is None:
            config = ExportConfig()

        model_abs_path = str(self.project_root / model_path)
        model_stem = Path(model_abs_path).stem
        output_path = self.project_root / "models" / f"{model_stem}.onnx"

        if progress_callback:
            progress_callback(10, "Loading model for ONNX export...")

        model = YOLO(model_abs_path)

        if progress_callback:
            progress_callback(30, "Exporting to ONNX format...")

        try:
            model.export(
                format="onnx",
                imgsz=config.imgsz,
                half=config.half,
                simplify=config.simplify,
            )
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"ONNX export failed: {e}")
            return None

        if progress_callback:
            progress_callback(100, f"ONNX export complete: {output_path}")

        return output_path

    def generate_deploy_package(
        self,
        model_path: str,
        output_dir: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Optional[tuple]:
        model_abs_path = self.project_root / model_path
        if not model_abs_path.exists():
            if progress_callback:
                progress_callback(0, f"Model not found: {model_abs_path}")
            return None

        model_stem = model_abs_path.stem
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir_path / f"deploy_package_{model_stem}.zip"

        tmp_dir = output_dir_path / f"_tmp_deploy_{model_stem}"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        models_tmp = tmp_dir / "models"
        models_tmp.mkdir(parents=True)

        try:
            if progress_callback:
                progress_callback(5, "Exporting TensorRT .engine...")
            engine_path = self.export_tensorrt(model_path)
            if engine_path and engine_path.exists():
                shutil.copy2(engine_path, models_tmp / engine_path.name)
                if progress_callback:
                    progress_callback(20, f"Copied {engine_path.name}")
            else:
                if progress_callback:
                    progress_callback(20, "TensorRT export skipped (not available on this GPU)")

            if progress_callback:
                progress_callback(30, "Exporting ONNX...")
            onnx_path = self.export_onnx(model_path)
            if onnx_path and onnx_path.exists():
                shutil.copy2(onnx_path, models_tmp / onnx_path.name)
                if progress_callback:
                    progress_callback(45, f"Copied {onnx_path.name}")

            if progress_callback:
                progress_callback(50, "Copying original model...")
            pt_dest = models_tmp / model_abs_path.name
            shutil.copy2(model_abs_path, pt_dest)

            if progress_callback:
                progress_callback(60, "Copying Jetson resources...")
            smoke_detect_src = self.project_root / "src" / "jetson" / "smoke_detect.py"
            if smoke_detect_src.exists():
                shutil.copy2(smoke_detect_src, tmp_dir / "smoke_detect.py")

            setup_sh_src = self.project_root / "scripts" / "setup_jetson.sh"
            if setup_sh_src.exists():
                shutil.copy2(setup_sh_src, tmp_dir / "setup_jetson.sh")

            req_src = self.project_root / "requirements_jetson.txt"
            if req_src.exists():
                shutil.copy2(req_src, tmp_dir / "requirements_jetson.txt")

            if progress_callback:
                progress_callback(70, "Creating README...")
            readme_content = (
                "=== Jetson Nano/TX2/Orin 部署说明 ===\n"
                "1. 将部署包解压到 Jetson 设备\n"
                "2. 运行: bash setup_jetson.sh 安装依赖\n"
                f"3. 测试: python3 smoke_detect.py --model models/{model_stem}.engine --video test.mp4\n"
                f"4. 生产: python3 smoke_detect.py --model models/{model_stem}.engine --rtsp rtsp://...\n"
            )
            readme_path = tmp_dir / "README_DEPLOY.txt"
            readme_path.write_text(readme_content, encoding="utf-8")

            if progress_callback:
                progress_callback(80, "Creating ZIP package...")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in tmp_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(tmp_dir)
                        zf.write(file_path, arcname)

            zip_size = zip_path.stat().st_size

            if progress_callback:
                progress_callback(
                    100,
                    f"Deploy package created: {zip_path} ({zip_size / 1024 / 1024:.1f} MB)",
                )

            return str(zip_path), zip_size

        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def verify_export(self, output_path: str) -> bool:
        p = Path(output_path)
        if not p.exists():
            return False
        if not p.is_file():
            return False
        if p.stat().st_size < 1024:
            return False
        return True
