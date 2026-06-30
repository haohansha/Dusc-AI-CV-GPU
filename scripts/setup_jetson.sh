#!/bin/bash
echo "=== Jetson Nano Smoke Detection Environment Check ==="
echo ""

echo "[1/5] Checking JetPack..."
if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    echo "  CUDA: OK"
else
    echo "  WARNING: CUDA not available. Please flash JetPack (4.6.x for Nano, 6.x for Orin Nano)"
fi

echo "[2/5] Checking TensorRT..."
if python3 -c "import tensorrt; print(tensorrt.__version__)" 2>/dev/null; then
    echo "  TensorRT: OK"
else
    echo "  WARNING: TensorRT not found"
fi

echo "[3/5] Checking ultralytics..."
if python3 -c "import ultralytics" 2>/dev/null; then
    VERSION=$(python3 -c "import ultralytics; print(ultralytics.__version__)" 2>/dev/null)
    echo "  ultralytics: OK ($VERSION)"
else
    echo "  WARNING: ultralytics not installed. Run: pip3 install ultralytics"
fi

echo "[4/5] Checking opencv-python..."
if python3 -c "import cv2" 2>/dev/null; then
    VERSION=$(python3 -c "import cv2; print(cv2.__version__)" 2>/dev/null)
    echo "  opencv-python: OK ($VERSION)"
else
    echo "  WARNING: opencv-python not installed. Run: pip3 install opencv-python"
fi

echo "[5/5] Checking CSI camera..."
if ls /dev/video* 2>/dev/null | grep -q video; then
    echo "  CSI camera device: OK"
    ls /dev/video*
else
    echo "  WARNING: No /dev/video* found. CSI camera may not be connected."
fi

echo ""
echo "=== Check Complete ==="
echo ""
echo "If all OK, transfer model & smoke_detect.py, then run:"
echo "  python3 smoke_detect.py --video test.mp4"
echo "  python3 smoke_detect.py --camera 0"
echo "  python3 smoke_detect.py --rtsp rtsp://admin:pass@192.168.1.100:554/Streaming/Channels/101"
