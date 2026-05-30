import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


def webcam_demo(model_path, camera_id=0, conf=0.25):
    model = YOLO(model_path)

    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {camera_id}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Camera opened. Press 'q' to quit.")
    print(f"Model: {model_path}, Confidence threshold: {conf}")

    fps_history = []
    frame_count = 0

    cv2.namedWindow("Smoke Detection - Webcam", cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Cannot read frame from camera")
            break

        t_start = time.time()
        results = model.predict(frame, conf=conf, verbose=False, device=0)
        inference_time = (time.time() - t_start) * 1000

        fps_history.append(1000 / inference_time)
        if len(fps_history) > 100:
            fps_history.pop(0)
        avg_fps = sum(fps_history) / len(fps_history)

        annotated_frame = results[0].plot()

        boxes = results[0].boxes
        if boxes is not None:
            for box in boxes:
                cls_id = int(box.cls[0])
                conf_val = float(box.conf[0])
                cls_name = result.names[cls_id]
                if conf_val > 0.5:
                    status = "HIGH" if cls_name == "smoke" else "ALERT"
                    color = (0, 0, 255) if cls_name == "smoke" else (0, 165, 255)
                    cv2.putText(annotated_frame, f"{cls_name}: {status}",
                                (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        fps_text = f"FPS: {avg_fps:.1f} | Model: YOLOv8n | GPU"
        cv2.putText(annotated_frame, fps_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Smoke Detection - Webcam", annotated_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()

    if fps_history:
        print(f"\nWebcam demo completed:")
        print(f"  Total frames: {frame_count}")
        print(f"  Average FPS: {sum(fps_history) / len(fps_history):.1f}")
        print(f"  Min FPS: {min(fps_history):.1f}")
        print(f"  Max FPS: {max(fps_history):.1f}")


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Smoke Detection - Webcam Demo")
    parser.add_argument("--model", type=str, default="models/smoke_detection_best.pt",
                        help="Path to model weights")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device ID")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold")

    args = parser.parse_args()
    webcam_demo(args.model, args.camera, args.conf)


if __name__ == "__main__":
    main()
