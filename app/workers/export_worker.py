from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from modules.export_engine import ExportConfig, ExportEngine


class ExportWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, project_root, export_func_name, model_path, config):
        super().__init__()
        self._project_root = Path(project_root)
        self._export_func_name = export_func_name
        self._model_path = model_path
        self._config = config

    def run(self):
        try:
            engine = ExportEngine(self._project_root)
            if self._export_func_name == "tensorrt":
                output_path = engine.export_tensorrt(
                    self._model_path,
                    self._config,
                    progress_callback=self._on_progress,
                )
                if output_path is not None:
                    self.finished.emit(str(output_path))
                else:
                    self.error.emit("TensorRT export returned no output path")
            elif self._export_func_name == "onnx":
                output_path = engine.export_onnx(
                    self._model_path,
                    self._config,
                    progress_callback=self._on_progress,
                )
                if output_path is not None:
                    self.finished.emit(str(output_path))
                else:
                    self.error.emit("ONNX export returned no output path")
            elif self._export_func_name == "deploy":
                output_dir = str(self._project_root / "exports")
                result = engine.generate_deploy_package(
                    self._model_path,
                    output_dir,
                    progress_callback=self._on_progress,
                )
                if result is not None:
                    zip_path, _ = result
                    self.finished.emit(str(zip_path))
                else:
                    self.error.emit("Deploy package generation failed")
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, pct, message):
        self.progress.emit(pct, message)
