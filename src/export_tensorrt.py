import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
venv_path = str(project_root / "venv" / "Lib" / "site-packages")
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

from modules.export_engine import ExportConfig, ExportEngine


def main():
    engine = ExportEngine(project_root)

    model_path = str(project_root / "models" / "factory_smoke_finetuned.pt")

    engine.export_tensorrt(
        model_path=model_path,
        config=ExportConfig(
            format="engine",
            imgsz=640,
            half=True,
            device=0,
            workspace=4,
            simplify=True,
            model_path=model_path,
        ),
    )

    engine.export_onnx(
        model_path=model_path,
        config=ExportConfig(
            format="onnx",
            imgsz=640,
            half=True,
            simplify=True,
            model_path=model_path,
        ),
    )

    print("Export complete:")


if __name__ == "__main__":
    main()
