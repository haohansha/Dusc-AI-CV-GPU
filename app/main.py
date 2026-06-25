import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent

os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

import torch

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from app.models.app_config import AppConfig
from app.main_window import MainWindow

def _load_theme(theme_name):
    if theme_name == "dark":
        qss_path = project_root / "app" / "resources" / "dark.qss"
        if qss_path.exists():
            return open(qss_path, "r", encoding="utf-8").read()
    return ""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("工业烟雾AI视觉识别与管理平台")

    config = AppConfig(project_root)

    theme = config.get("theme", "light")
    theme_qss = _load_theme(theme)
    if theme_qss:
        app.setStyleSheet(theme_qss)

    try:
        window = MainWindow(config)
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "启动错误", f"应用程序启动失败:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
