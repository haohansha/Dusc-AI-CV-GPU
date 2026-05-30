import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO


def detect_image(model_path, image_path, conf=0.25, save=True, show=False):
    project_root = Path(__file__).parent.parent
    model = YOLO(model_path)

    results = model.predict(
        source=image_path,
        conf=conf,
        save=save,
        show=show,
        project=str(project_root / "runs" / "detect"),
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

    return results


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 Smoke Detection - Image Inference")
    parser.add_argument("--model", type=str, default="models/smoke_detection_best.pt",
                        help="Path to model weights")
    parser.add_argument("--image", type=str, required=True,
                        help="Path to input image")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not save results")
    parser.add_argument("--show", action="store_true",
                        help="Show results in window")

    args = parser.parse_args()
    detect_image(args.model, args.image, args.conf, not args.no_save, args.show)


if __name__ == "__main__":
    main()
