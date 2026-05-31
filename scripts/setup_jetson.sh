#!/bin/bash
echo "=== Jetson Orin Nano Smoke Detection Setup ==="
echo ""

echo "[1/4] Checking JetPack..."
if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    echo "  CUDA: OK"
else
    echo "  WARNING: CUDA not available. Please flash JetPack 6.x"
fi

echo "[2/4] Checking TensorRT..."
if python3 -c "import tensorrt; print(tensorrt.__version__)" 2>/dev/null; then
    echo "  TensorRT: OK"
else
    echo "  WARNING: TensorRT not found"
fi

echo "[3/4] Installing dependencies..."
pip install ultralytics opencv-python

echo "[4/4] Verifying ultralytics..."
python3 -c "from ultralytics import YOLO; print('  ultralytics: OK')"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run smoke detection:"
echo "  python3 smoke_detect.py --video test.mp4"
echo "  python3 smoke_detect.py --camera 0"
echo "  python3 smoke_detect.py --rtsp rtsp://admin:pass@192.168.1.100:554/Streaming/Channels/101"
