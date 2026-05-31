import argparse, cv2, time, sys
from pathlib import Path
from ultralytics import YOLO

FAN_SPEEDS = {"LIGHT": 20, "MEDIUM": 50, "HEAVY": 100}
prev_level = None


def fan_control(level, conf, area_pct, ms):
    global prev_level
    duty = FAN_SPEEDS.get(level, 0)
    if level != prev_level:
        if level == "NONE":
            print(f"\n{'='*50}")
            print(f"  FAN STOP  | no smoke detected")
            print(f"{'='*50}")
        else:
            print(f"\n{'='*50}")
            print(f"  FAN: {duty}% ({level}) | Conf={conf:.2f} | Area={area_pct:.1f}% | {ms:.1f}ms")
            print(f"     simulated: GPIO PWM={duty}% -> fan controller")
            print(f"{'='*50}")
        prev_level = level


class SmokeDetector:
    def __init__(self, model_path, conf=0.3):
        self.model = YOLO(model_path)
        self.conf = conf
        self.names = self.model.names
        print(f"Model loaded: {Path(model_path).name}")
        print(f"Classes: {self.names}")
        print(f"Confidence threshold: {conf}")

    def detect(self, frame):
        t0 = time.time()
        results = self.model.predict(frame, conf=self.conf, verbose=False, device=0)
        ms = (time.time() - t0) * 1000

        boxes = results[0].boxes
        info = {"has_smoke": False, "detections": [], "inference_ms": ms,
                "level": "NONE", "fan_speed": 0}

        if boxes is not None:
            h, w = frame.shape[:2]
            smoke_confs = []
            smoke_areas = []
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = self.names[cls_id]
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                area_pct = ((x2-x1)*(y2-y1) / (w*h)) * 100
                d = {"class": cls_name, "conf": conf_val,
                     "bbox": [x1, y1, x2, y2], "area_pct": area_pct}
                info["detections"].append(d)
                if "smoke" in cls_name.lower():
                    info["has_smoke"] = True
                    smoke_confs.append(conf_val)
                    smoke_areas.append(area_pct)

            if info["has_smoke"]:
                max_conf = max(smoke_confs)
                max_area = max(smoke_areas)
                if max_area > 20 or max_conf > 0.7:
                    info["level"] = "HEAVY"
                    info["fan_speed"] = 100
                elif max_area > 10 or max_conf > 0.5:
                    info["level"] = "MEDIUM"
                    info["fan_speed"] = 50
                else:
                    info["level"] = "LIGHT"
                    info["fan_speed"] = 20

        return info


def main():
    parser = argparse.ArgumentParser(description="Jetson Smoke Detection Demo")
    parser.add_argument("--model", default="factory_smoke_finetuned.pt")
    parser.add_argument("--conf", type=float, default=0.3)
    parser.add_argument("--video", help="video file path")
    parser.add_argument("--camera", type=int, default=0, help="camera device ID")
    parser.add_argument("--rtsp", help="RTSP URL")
    args = parser.parse_args()

    detector = SmokeDetector(args.model, args.conf)

    if args.video:
        cap = cv2.VideoCapture(args.video)
        input_name = f"Video: {args.video}"
    elif args.rtsp:
        cap = cv2.VideoCapture(args.rtsp, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        input_name = f"RTSP: {args.rtsp}"
    else:
        cap = cv2.VideoCapture(args.camera)
        input_name = f"Camera #{args.camera}"

    if not cap.isOpened():
        print(f"Error: Cannot open {input_name}")
        sys.exit(1)

    fps_vid = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{input_name} | {w}x{h} | {fps_vid:.1f} FPS")
    print("Press Ctrl+C to stop\n")

    frame_count = 0
    total_ms = 0
    log_interval = 30

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if args.video:
                    break
                else:
                    continue

            frame_count += 1
            result = detector.detect(frame)
            total_ms += result["inference_ms"]

            if result["has_smoke"] or prev_level is not None:
                max_c = max((d["conf"] for d in result["detections"]
                            if "smoke" in d["class"].lower()), default=0)
                max_a = max((d["area_pct"] for d in result["detections"]
                            if "smoke" in d["class"].lower()), default=0)
                fan_control(result["level"], max_c, max_a, result["inference_ms"])

            if frame_count % log_interval == 0:
                avg_ms = total_ms / frame_count
                fps = 1000 / avg_ms if avg_ms > 0 else 0
                print(f"  [{frame_count:6d} frames] avg {avg_ms:.1f}ms ({fps:.1f} FPS)")

    except KeyboardInterrupt:
        print("\nStopped by user")

    cap.release()
    avg_ms = total_ms / frame_count if frame_count > 0 else 0
    print(f"\n=== Summary ===")
    print(f"Total frames: {frame_count}")
    if avg_ms > 0:
        print(f"Avg inference: {avg_ms:.1f}ms ({1000/avg_ms:.1f} FPS)")


if __name__ == "__main__":
    main()
