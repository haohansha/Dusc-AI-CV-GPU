from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from modules.model_manager import ModelManager
from modules.dataset_manager import DatasetManager


class ImportWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, project_root, task_type, params):
        super().__init__()
        self._project_root = Path(project_root)
        self._task_type = task_type
        self._params = params

    def run(self):
        try:
            if self._task_type == "import_model":
                self.progress.emit(10, "Importing model...")
                manager = ModelManager(self._project_root)
                source_path = Path(self._params["source_path"])
                result = manager.import_model(source_path)
                self.progress.emit(100, "Model import complete")
                self.finished.emit(result)
            elif self._task_type == "download_yolo":
                self.progress.emit(10, "Downloading YOLO model...")
                manager = ModelManager(self._project_root)
                model_size = self._params.get("model_size", "n")
                result = manager.download_yolo(model_size)
                self.progress.emit(100, "YOLO model download complete")
                self.finished.emit(result)
            elif self._task_type == "import_video":
                self.progress.emit(10, "Importing video...")
                manager = DatasetManager(self._project_root)
                source_path = self._params["source_path"]
                self.progress.emit(40, "Copying video file...")
                result = manager.import_video(source_path)
                self.progress.emit(100, "Video import complete")
                self.finished.emit(result)
            elif self._task_type == "import_images":
                self.progress.emit(10, "Importing images...")
                manager = DatasetManager(self._project_root)
                source_paths = self._params["source_paths"]
                total = len(source_paths)
                for i, src in enumerate(source_paths):
                    pct = 10 + int(80 * (i + 1) / total)
                    self.progress.emit(pct, f"Importing image {i + 1}/{total}...")
                result = manager.import_images(source_paths)
                self.progress.emit(100, "Image import complete")
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
