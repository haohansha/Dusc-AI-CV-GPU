import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import cv2
from ultralytics import YOLO


@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    bbox: tuple
    area_pct: float


@dataclass
class InferenceConfig:
    model_path: str
    conf: float = 0.25
    device: int = 0


class InferenceEngine:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    def _load_model(self, model_path):
        return YOLO(model_path)

    def _extract_detections(self, result, frame_shape):
        detections = []
        h, w = frame_shape[:2]
        frame_area = w * h
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                area_pct = ((x2 - x1) * (y2 - y1) / frame_area) * 100
                detections.append(DetectionResult(
                    class_name=cls_name,
                    confidence=conf_val,
                    bbox=(x1, y1, x2, y2),
                    area_pct=area_pct,
                ))
        return detections

    def process_frame(self, frame, model, conf):
        t_start = time.time()
        results = model.predict(frame, conf=conf, verbose=False, device=0)
        inference_ms = (time.time() - t_start) * 1000
        annotated_frame = results[0].plot()
        detections = self._extract_detections(results[0], frame.shape)
        return annotated_frame, detections, inference_ms

    def detect_image(self, image_path, model_path, conf=0.25, save=True):
        model = self._load_model(model_path)
        results = model.predict(
            source=image_path,
            conf=conf,
            save=save,
            project=str(self.project_root / "runs" / "detect"),
            name="image_result",
            exist_ok=True,
        )
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                print(f"Detected {len(boxes)} objects in {image_path}")
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = result.names[cls_id]
                    conf_val = float(box.conf[0])
                    print(f"  - {cls_name}: {conf_val:.2%}")
            h, w = result.orig_shape[:2]
            detections = self._extract_detections(result, (h, w))
            return detections
        return []

    def detect_video(self, video_path, model_path, conf=0.25, save=True, output_dir=None, progress_callback=None):
        model = self._load_model(model_path)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Cannot open video source: {video_path}")
            return None

        fps_input = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Video: {width}x{height}, {fps_input:.1f} FPS, {total_frames} frames")

        base_dir = Path(output_dir) if output_dir else self.project_root
        output_dir_path = base_dir / "runs" / "detect" / "video_result"
        output_dir_path.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        output_path = str(output_dir_path / "output.mp4")
        writer = cv2.VideoWriter(output_path, fourcc, fps_input, (width, height)) if save else None

        frame_count = 0
        total_inference_time = 0
        total_detections = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            t_start = time.time()

            results = model.predict(frame, conf=conf, verbose=False, device=0)

            inference_ms = (time.time() - t_start) * 1000
            total_inference_time += inference_ms

            annotated_frame = results[0].plot()
            detections = self._extract_detections(results[0], frame.shape)
            total_detections += len(detections)

            fps_text = f"FPS: {1000 / inference_ms:.1f}"
            cv2.putText(annotated_frame, fps_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            if writer:
                writer.write(annotated_frame)

            if progress_callback:
                progress_callback(frame_count, total_frames, annotated_frame, detections, inference_ms)

            if frame_count % 100 == 0:
                avg_fps = 1000 / (total_inference_time / frame_count)
                print(f"Processed {frame_count}/{total_frames} frames, "
                      f"avg inference: {inference_ms:.1f}ms ({avg_fps:.1f} FPS)")

        cap.release()
        if writer:
            writer.release()

        avg_fps = 1000 / (total_inference_time / frame_count) if frame_count > 0 else 0
        avg_inference_ms = total_inference_time / frame_count if frame_count > 0 else 0

        stats = {
            'total_frames': frame_count,
            'avg_fps': avg_fps,
            'avg_inference_ms': avg_inference_ms,
            'total_detections': total_detections,
        }

        print(f"\nProcessing completed:")
        print(f"  Total frames: {frame_count}")
        print(f"  Average inference time: {avg_inference_ms:.1f}ms")
        print(f"  Average FPS: {avg_fps:.1f}")
        if save:
            print(f"  Output saved to: {output_path}")

        return stats

    def detect_camera(self, camera_id, model_path, conf=0.25, frame_callback=None):
        model = self._load_model(model_path)
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print(f"Error: Cannot open camera {camera_id}")
            return

        try:
            fps_history = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                t_start = time.time()
                results = model.predict(frame, conf=conf, verbose=False, device=0)
                inference_ms = (time.time() - t_start) * 1000

                annotated_frame = results[0].plot()
                detections = self._extract_detections(results[0], frame.shape)

                fps = 1000 / inference_ms if inference_ms > 0 else 0
                fps_history.append(fps)
                if len(fps_history) > 100:
                    fps_history.pop(0)
                avg_fps = sum(fps_history) / len(fps_history)

                if frame_callback:
                    if frame_callback(annotated_frame, detections, avg_fps, inference_ms) is False:
                        break
        except KeyboardInterrupt:
            pass
        finally:
            cap.release()
