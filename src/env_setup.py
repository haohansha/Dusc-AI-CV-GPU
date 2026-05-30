import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_path = os.path.join(project_root, 'venv', 'Lib', 'site-packages')

if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

os.environ.setdefault('YOLO_CONFIG_DIR', os.path.join(project_root, '.ultralytics'))

config_dir = os.path.join(project_root, '.ultralytics', 'Ultralytics')
os.makedirs(config_dir, exist_ok=True)
