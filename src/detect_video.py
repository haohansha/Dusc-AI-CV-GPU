import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


def detect_video(model_path, video_path, conf=0.25, save=True, show=False):
    project_root = Path(__file__).parent.parent
    model = YOLO(model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video source: {video_path}")
        return

    fps_input = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video: {width}x{height}, {fps_input:.1f} FPS, {total_frames} frames")

    output_dir = project_root / "runs" / "detect" / "video_result"
    output_dir.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_path = str(output_dir / "output.mp4")
    writer = cv2.VideoWriter(output_path, fourcc, fps_input, (width, height)) if save else None

    frame_count = 0
    total_inference_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        t_start = time.time()

        results = model.predict(frame, conf=conf, verbose=False, device=0)

        inference_time = (time.time() - t_start) * 1000
        total_inference_time += inference_time

        annotated_frame = results[0].plot()

        fps_text = f"FPS: {1000 / inference_time:.1f}"
        cv2.putText(annotated_frame, fps_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if writer:
            writer.write(annotated_frame)

        if show:
            cv2.imshow("Smoke Detection", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if frame_count % 100 == 0:
            avg_fps = 1000 / (total_inference_time / frame_count)
            print(f"Processed {frame_count}/{total_frames} frames, "
                  f"avg inference: {inference_time:.1f}ms ({avg_fps:.1f} FPS)")

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()

    avg_fps = 1000 / (total_inference_time / frame_count) if frame_count > 0 else 0
    print(f"\nProcessing completed:")
    print(f"  Total frames: {frame_count}")
    print(f"  Average inference time: {total_inference_time / frame_count:.1f}ms")
    print(f"  Average FPS: {avg_fps:.1f}")
    if save:
        print(f"  Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Smoke Detection - Video Inference")
    parser.add_argument("--model", type=str, default="models/smoke_detection_best.pt",
                        help="Path to model weights")
    parser.add_argument("--video", type=str, required=True,
                        help="Path to input video")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not save output video")
    parser.add_argument("--show", action="store_true",
                        help="Show results in window")

    args = parser.parse_args()
    detect_video(args.model, args.video, args.conf, not args.no_save, args.show)


if __name__ == "__main__":
    main()
