import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
venv_path = str(project_root / "venv" / "Lib" / "site-packages")
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

import cv2
from ultralytics import YOLO


def load_models():
    old_path = project_root / "models" / "smoke_detection_best.pt"
    new_path = project_root / "models" / "factory_smoke_finetuned.pt"

    old_model = YOLO(str(old_path)) if old_path.exists() else None
    new_model = YOLO(str(new_path)) if new_path.exists() else None

    if old_model is None:
        print("Warning: Old model not found, skip comparison")
    if new_model is None:
        print("Warning: New model not found, skip comparison")
    return old_model, new_model


def collect_stats(model, frame, conf=0.3):
    t_start = time.time()
    results = model.predict(frame, conf=conf, verbose=False, device=0)
    ms = (time.time() - t_start) * 1000

    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return {"detections": 0, "total_conf": 0.0, "avg_conf": 0.0,
                "total_area_pct": 0.0, "inference_ms": ms, "has_smoke": False}

    h, w = frame.shape[:2]
    total_area = w * h
    total_conf = 0.0
    total_area_pct = 0.0
    has_smoke = False

    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = results[0].names[cls_id]
        conf_val = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        box_area = (x2 - x1) * (y2 - y1)

        if "smoke" in cls_name.lower():
            has_smoke = True
            total_conf += conf_val
            total_area_pct += (box_area / total_area) * 100

    num = sum(1 for b in boxes if "smoke" in results[0].names[int(b.cls[0])].lower())
    return {
        "detections": num,
        "total_conf": total_conf,
        "avg_conf": total_conf / num if num > 0 else 0.0,
        "total_area_pct": total_area_pct,
        "inference_ms": ms,
        "has_smoke": has_smoke,
    }


def compare_models(video_path, sample_interval=10):
    old_model, new_model = load_models()
    if old_model is None and new_model is None:
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {video_path}")
        return

    fps_vid = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    old_stats = {"frames_with_smoke": 0, "total_detections": 0,
                 "total_conf": 0.0, "total_area_pct": 0.0, "total_ms": 0.0, "samples": 0}
    new_stats = {"frames_with_smoke": 0, "total_detections": 0,
                 "total_conf": 0.0, "total_area_pct": 0.0, "total_ms": 0.0, "samples": 0}

    frame_idx = 0
    sample_count = 0
    print(f"Comparing models on: {Path(video_path).name}")
    print(f"Total frames: {total_frames}, Sampling every {sample_interval} frames\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval != 0:
            frame_idx += 1
            continue

        sample_count += 1

        if old_model is not None:
            s = collect_stats(old_model, frame)
            old_stats["samples"] += 1
            old_stats["total_ms"] += s["inference_ms"]
            if s["has_smoke"]:
                old_stats["frames_with_smoke"] += 1
                old_stats["total_detections"] += s["detections"]
                old_stats["total_conf"] += s["total_conf"]
                old_stats["total_area_pct"] += s["total_area_pct"]

        if new_model is not None:
            s = collect_stats(new_model, frame)
            new_stats["samples"] += 1
            new_stats["total_ms"] += s["inference_ms"]
            if s["has_smoke"]:
                new_stats["frames_with_smoke"] += 1
                new_stats["total_detections"] += s["detections"]
                new_stats["total_conf"] += s["total_conf"]
                new_stats["total_area_pct"] += s["total_area_pct"]

        frame_idx += 1

    cap.release()

    def avg(v, n):
        return v / n if n > 0 else 0

    print("=" * 68)
    print("          烟雾检测模型微调前后对比")
    print("=" * 68)
    print(f"视频: {Path(video_path).name} | 采样帧数: {sample_count} (每{sample_interval}帧)")
    print()

    print(f"{'指标':<28} {'旧模型':>12} {'新模型':>12} {'变化':>10}")
    print("-" * 68)

    os_val = old_stats["samples"]
    ns_val = new_stats["samples"]

    of = old_stats["frames_with_smoke"]
    nf = new_stats["frames_with_smoke"]
    ofp = of / os_val * 100 if os_val > 0 else 0
    nfp = nf / ns_val * 100 if ns_val > 0 else 0
    print(f"{'检测到烟雾的帧数':<28} {of:>12} {nf:>12} {nf-of:>+10}")

    print(f"{'检测到烟雾的帧占比':<28} {ofp:>11.1f}% {nfp:>11.1f}% {nfp-ofp:>+9.1f}%")

    od = old_stats["total_detections"]
    nd = new_stats["total_detections"]
    print(f"{'总检测目标数':<28} {od:>12} {nd:>12} {nd-od:>+10}")

    oac = avg(old_stats["total_conf"], of)
    nac = avg(new_stats["total_conf"], nf)
    print(f"{'平均置信度':<28} {oac:>12.4f} {nac:>12.4f} {nac-oac:>+10.4f}")

    oaa = avg(old_stats["total_area_pct"], of)
    naa = avg(new_stats["total_area_pct"], nf)
    print(f"{'平均检测框面积占比(%)':<28} {oaa:>11.2f} {naa:>11.2f} {naa-oaa:>+9.2f}")

    oms = avg(old_stats["total_ms"], old_stats["samples"])
    nms = avg(new_stats["total_ms"], new_stats["samples"])
    print(f"{'平均推理速度(ms/帧)':<28} {oms:>11.2f} {nms:>11.2f} {nms-oms:>+9.2f}")

    print("-" * 68)
    print()

    if nf > of:
        print(f"新模型在 {nfp-ofp:.1f}% 更多帧中检测到烟雾")
    if nac > oac:
        print(f"新模型平均置信度提升 {nac-oac:.4f}")
    if nd > od:
        print(f"新模型检测到 {nd-od} 个额外烟雾目标")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare old vs new smoke detection model")
    parser.add_argument("--video", type=str, required=True, help="Path to input video")
    parser.add_argument("--interval", type=int, default=10,
                        help="Sample every N frames (default: 10)")

    args = parser.parse_args()
    compare_models(args.video, args.interval)


if __name__ == "__main__":
    main()
