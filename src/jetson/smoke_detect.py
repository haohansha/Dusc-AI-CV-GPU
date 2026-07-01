import argparse, cv2, time, sys, subprocess
import numpy as np
from pathlib import Path
from ultralytics import YOLO

FAN_SPEEDS = {"LIGHT": 20, "MEDIUM": 50, "HEAVY": 100}
prev_level = None

# 颜色 (B, G, R)
COLORS = {
    "smoke":  (0, 0, 255),       # 红
    "fire":   (0, 165, 255),    # 橙
    "default":(255, 255, 0),    # 青
    "_level": {                  # 等级颜色
        "LIGHT":  (0, 255, 255),   # 黄
        "MEDIUM": (0, 165, 255),   # 橙
        "HEAVY":  (0, 0, 255),     # 红
        "NONE":   (0, 200, 0),     # 绿
    },
}


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

    def draw(self, frame, info):
        """在画面上叠加检测框、类别、置信度、风扇等级"""
        annotated = frame.copy()
        for d in info["detections"]:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            cls = d["class"]
            color = COLORS.get(cls.lower(), (255, 255, 255))
            label = f"{cls} {d['conf']:.2f} ({d['area_pct']:.1f}%)"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            # 标签背景
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # 左上角：风扇等级 + FPS + 帧数
        level = info["level"]
        lc = COLORS["_level"].get(level, (255, 255, 255))
        ms = info["inference_ms"]
        fps = 1000.0 / ms if ms > 0 else 0
        hud_lines = [
            f"Level: {level}  Fan: {info['fan_speed']}%",
            f"Inference: {ms:.1f}ms  FPS: {fps:.1f}",
            f"Smoke: {'YES' if info['has_smoke'] else 'NO'}  Boxes: {len(info['detections'])}",
        ]
        for i, line in enumerate(hud_lines):
            y = 20 + i * 22
            cv2.rectangle(annotated, (0, y - 16), (320, y + 4), (0, 0, 0), -1)
            cv2.putText(annotated, line, (6, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, lc, 1, cv2.LINE_AA)
        return annotated


class GstSubprocessCapture:
    """通过 gst-launch-1.0 子进程读取 CSI 摄像头，绕过 OpenCV GStreamer 集成问题。
    接口与 cv2.VideoCapture 兼容（isOpened/read/release/get）。"""

    def __init__(self, sensor_id=0, width=640, height=480, framerate=30):
        self.w = width
        self.h = height
        self.fps = framerate
        self.frame_size = width * height * 3  # BGR 三通道
        cmd = [
            "gst-launch-1.0", "-q",
            "nvarguscamerasrc", f"sensor_id={sensor_id}",
            "!", f"video/x-raw(memory:NVMM),width={width},height={height},format=NV12,framerate={framerate}/1",
            "!", "nvvidconv",
            "!", "video/x-raw,format=BGRx",
            "!", "videoconvert",
            "!", "video/x-raw,format=BGR",
            "!", "fdsink", "fd=1", "sync=false",
        ]
        # bufsize 设为一个完整帧，避免 read() 返回不完整数据
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=self.frame_size,
        )
        # Argus daemon 启动需要 1~2 秒
        time.sleep(1.5)
        self._opened = self.proc.poll() is None

    def isOpened(self):
        return self._opened and self.proc.poll() is None

    def read(self):
        raw = self.proc.stdout.read(self.frame_size)
        if len(raw) < self.frame_size:
            return False, None
        # copy() 避免后续 ultralytics/imshow 写入只读缓冲
        frame = np.frombuffer(raw, dtype=np.uint8).reshape(self.h, self.w, 3).copy()
        return True, frame

    def get(self, prop):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.w)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.h)
        if prop == cv2.CAP_PROP_FPS:
            return float(self.fps)
        return 0.0

    def release(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self._opened = False


def open_camera(camera_id):
    """通过 gst-launch-1.0 子进程打开 CSI 摄像头（绕过 OpenCV GStreamer 集成问题）。
    camera_id 在这里作为 nvarguscamerasrc 的 sensor_id 使用。"""
    print(f"  Opening CSI camera via gst-launch-1.0 subprocess (sensor_id={camera_id})...")
    try:
        cap = GstSubprocessCapture(sensor_id=camera_id, width=640, height=480)
        if cap.isOpened():
            # 读一帧验证是否真的有效
            ret, frame = cap.read()
            if ret and frame is not None and frame.mean() > 5:
                print(f"  CSI camera opened OK ({frame.shape})")
                return cap
            print(f"  No valid frame from gst-launch")
            cap.release()
        else:
            print(f"  gst-launch-1.0 failed to start")
    except FileNotFoundError:
        print(f"  gst-launch-1.0 not found in PATH")
    except Exception as e:
        print(f"  gst-launch-1.0 error: {e}")

    # 最后的回退：普通 V4L2（CSI 通常不可用，但 USB 摄像头可用）
    print(f"  Falling back to V4L2 (index={camera_id})")
    return cv2.VideoCapture(camera_id)


def main():
    parser = argparse.ArgumentParser(description="Jetson Smoke Detection Demo")
    parser.add_argument("--model", default="factory_smoke_finetuned.pt")
    parser.add_argument("--conf", type=float, default=0.3)
    parser.add_argument("--video", help="video file path")
    parser.add_argument("--camera", type=int, default=0, help="camera device ID (CSI camera recommended)")
    parser.add_argument("--rtsp", help="RTSP URL")
    parser.add_argument("--show", action="store_true", help="display window with annotations")
    parser.add_argument("--save", help="optional output video path")
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
        print("Opening CSI camera...")
        cap = open_camera(args.camera)
        input_name = f"Camera #{args.camera}"

    if not cap.isOpened():
        print(f"Error: Cannot open {input_name}")
        sys.exit(1)

    fps_vid = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{input_name} | {w}x{h} | {fps_vid:.1f} FPS")
    print("Press Ctrl+C to stop")
    if args.show:
        print("Press Q in display window to stop\n")
    else:
        print()

    writer = None
    if args.save:
        # Nano 上 mp4v 可能静默失败，根据后缀选择更稳的 fourcc
        ext = Path(args.save).suffix.lower()
        if ext == ".avi":
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
        elif ext == ".mp4":
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        else:
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(args.save, fourcc, 20.0, (w, h))
        if not writer.isOpened():
            print(f"Warning: cannot open writer for {args.save}, saving disabled")
            writer = None
        else:
            print(f"Saving to: {args.save} ({w}x{h} @ 20 FPS, fourcc={'XVID' if ext!='.mp4' else 'mp4v'})")

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

            if args.show or args.save:
                annotated = detector.draw(frame, result)
                if args.save and writer is not None:
                    writer.write(annotated)
                if args.show:
                    cv2.imshow("Smoke Detection (press Q to quit)", annotated)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord('q'), ord('Q'), 27):  # Q or ESC
                        print("\nStopped by window key")
                        break

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

    if args.show:
        cv2.destroyAllWindows()
    if writer is not None:
        writer.release()
    cap.release()
    avg_ms = total_ms / frame_count if frame_count > 0 else 0
    print(f"\n=== Summary ===")
    print(f"Total frames: {frame_count}")
    if avg_ms > 0:
        print(f"Avg inference: {avg_ms:.1f}ms ({1000/avg_ms:.1f} FPS)")


if __name__ == "__main__":
    main()
