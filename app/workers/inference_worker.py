from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import cv2
import numpy as np
from modules.inference_engine import InferenceEngine


class InferenceWorker(QThread):
    progress = pyqtSignal(int, int)
    frame_processed = pyqtSignal(bytes, list, float)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, project_root, model_path, video_path, conf):
        super().__init__()
        self._project_root = Path(project_root)
        self._model_path = model_path
        self._video_path = video_path
        self._conf = conf

    def run(self):
        try:
            engine = InferenceEngine(self._project_root)

            def progress_callback(frame_idx, total, annotated_frame, detections, inference_ms):
                self.progress.emit(frame_idx, total)
                _, png_bytes = cv2.imencode(".png", annotated_frame)
                detections_list = [
                    {
                        "class_name": d.class_name,
                        "confidence": d.confidence,
                        "bbox": d.bbox,
                        "area_pct": d.area_pct,
                    }
                    for d in detections
                ]
                self.frame_processed.emit(png_bytes.tobytes(), detections_list, inference_ms)

            stats = engine.detect_video(
                self._video_path,
                self._model_path,
                conf=self._conf,
                progress_callback=progress_callback,
            )
            if stats is not None:
                self.finished.emit(stats)
            else:
                self.error.emit("Video detection returned no stats")
        except Exception as e:
            self.error.emit(str(e))
