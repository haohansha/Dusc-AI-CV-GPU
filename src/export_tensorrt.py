import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
venv_path = str(project_root / "venv" / "Lib" / "site-packages")
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

from ultralytics import YOLO

model = YOLO(str(project_root / "models" / "factory_smoke_finetuned.pt"))

model.export(
    format="engine",
    imgsz=640,
    half=True,
    device=0,
    workspace=4,
    simplify=True,
)

model.export(
    format="onnx",
    imgsz=640,
    half=True,
    simplify=True,
)

print("Export complete:")
print(f"  {project_root / 'models' / 'factory_smoke_finetuned.engine'}")
print(f"  {project_root / 'models' / 'factory_smoke_finetuned.onnx'}")
