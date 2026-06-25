import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent

from modules.inference_engine import InferenceEngine


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

    args = parser.parse_args()

    engine = InferenceEngine(project_root)
    detections = engine.detect_image(
        image_path=args.image,
        model_path=args.model,
        conf=args.conf,
        save=not args.no_save,
    )
    print(f"Detections: {len(detections)}")


if __name__ == "__main__":
    main()
