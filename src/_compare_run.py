import sys, os, time
sys.path.insert(0, r'e:\project\Dusc AI CV GPU\venv\Lib\site-packages')
os.environ['YOLO_CONFIG_DIR'] = r'e:\project\Dusc AI CV GPU\.ultralytics'
import cv2, gc
from ultralytics import YOLO

def run_model(model_path, video_path, interval=10):
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)
    frames_with_smoke = 0
    total_det = 0
    total_conf = 0.0
    total_area = 0.0
    total_ms = 0.0
    samples = 0
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_idx % interval != 0:
            frame_idx += 1
            continue
        samples += 1
        h, w = frame.shape[:2]
        t0 = time.time()
        results = model.predict(frame, conf=0.3, verbose=False, device=0)
        ms = (time.time() - t0) * 1000
        total_ms += ms
        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            has_smoke = False
            for b in boxes:
                cls_name = results[0].names[int(b.cls[0])]
                if 'smoke' in cls_name.lower():
                    has_smoke = True
                    conf_val = float(b.conf[0])
                    x1,y1,x2,y2 = b.xyxy[0].tolist()
                    total_conf += conf_val
                    total_area += ((x2-x1)*(y2-y1)/(w*h))*100
                    total_det += 1
            if has_smoke:
                frames_with_smoke += 1
        frame_idx += 1
    cap.release()
    del model; gc.collect()
    
    if samples == 0: return None
    return {
        'smoke_frames': frames_with_smoke,
        'smoke_pct': frames_with_smoke/samples*100,
        'total_det': total_det,
        'avg_conf': total_conf/total_det if total_det>0 else 0,
        'avg_area': total_area/total_det if total_det>0 else 0,
        'avg_ms': total_ms/samples,
        'samples': samples,
    }

video = r'e:\project\Dusc AI CV GPU\videos\VID_20230501_160954.mp4'
print('Running OLD model...')
old = run_model(r'e:\project\Dusc AI CV GPU\models\smoke_detection_best.pt', video, 10)
print('Running NEW model...')
new = run_model(r'e:\project\Dusc AI CV GPU\models\factory_smoke_finetuned.pt', video, 10)

if old is None or new is None:
    print('Error: model inference failed')
    sys.exit(1)

print()
print('=' * 68)
print('           yan wu jian ce mo xing wei tiao qian hou dui bi')
print('=' * 68)
print(f'Video: VID_20230501_160954.mp4 | Samples: {old["samples"]}')
print()
header = '%-28s %12s %12s %10s' % ('Indicator', 'OLD', 'NEW', 'Delta')
print(header)
print('-' * 68)
print('%-28s %12d %12d %+10d' % ('Smoke frames', old['smoke_frames'], new['smoke_frames'], new['smoke_frames']-old['smoke_frames']))
print('%-28s %11.1f%% %11.1f%% %+9.1f%%' % ('Smoke frame rate', old['smoke_pct'], new['smoke_pct'], new['smoke_pct']-old['smoke_pct']))
print('%-28s %12d %12d %+10d' % ('Total detections', old['total_det'], new['total_det'], new['total_det']-old['total_det']))
print('%-28s %12.4f %12.4f %+10.4f' % ('Avg confidence', old['avg_conf'], new['avg_conf'], new['avg_conf']-old['avg_conf']))
print('%-28s %11.2f %11.2f %+9.2f' % ('Avg box area (%)', old['avg_area'], new['avg_area'], new['avg_area']-old['avg_area']))
print('%-28s %11.2f %11.2f %+9.2f' % ('Avg speed (ms/frame)', old['avg_ms'], new['avg_ms'], new['avg_ms']-old['avg_ms']))
print('-' * 68)
