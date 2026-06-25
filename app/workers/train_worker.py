from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from modules.train_engine import TrainingConfig, TrainEngine


class TrainWorker(QThread):
    progress = pyqtSignal(int, int, dict)
    log_message = pyqtSignal(str, str)
    finished = pyqtSignal(str, dict)
    error = pyqtSignal(str)

    def __init__(self, project_root, config):
        super().__init__()
        self._project_root = Path(project_root)
        self._config = config
        self._train_engine = None

    def run(self):
        try:
            self._train_engine = TrainEngine(self._project_root)
            best_model_path = self._train_engine.train(
                self._config, callback=self._on_progress
            )
            metrics = self._train_engine._read_metrics(
                self._config.project, self._config.name
            )
            self.finished.emit(str(best_model_path), metrics)
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, epoch, total, metrics):
        self.progress.emit(epoch, total, metrics)

    def stop(self):
        if self._train_engine:
            self._train_engine.stop()
