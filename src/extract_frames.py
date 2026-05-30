import argparse
import os
from pathlib import Path

import cv2


def extract_frames(video_path, interval=15, output_dir=None, max_frames=None):
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        return

    if output_dir is None:
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "factory_frames"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    video_name = video_path.stem

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Error: Cannot open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"Video: {video_name}")
    print(f"  FPS: {fps:.1f} | Total frames: {total_frames} | Duration: {duration:.1f}s")
    print(f"  Extract interval: every {interval} frames (~{fps/interval:.1f} per second)")
    print(f"  Output: {output_dir}")

    extracted = 0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval == 0:
            filename = f"{video_name}_frame_{frame_idx:06d}.jpg"
            output_path = output_dir / filename
            cv2.imwrite(str(output_path), frame)
            extracted += 1

            if extracted % 20 == 0:
                print(f"  Extracted {extracted} frames... (frame {frame_idx}/{total_frames})")

        frame_idx += 1

        if max_frames and extracted >= max_frames:
            break

    cap.release()

    print(f"\nDone: {extracted} frames extracted from {video_name}")
    print(f"Output directory: {output_dir}")

    return extracted


def main():
    parser = argparse.ArgumentParser(description="Extract key frames from video for annotation")
    parser.add_argument("--video", type=str, required=True, help="Path to input video")
    parser.add_argument("--interval", type=int, default=15,
                        help="Extract every N frames (default: 15)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory (default: data/factory_frames/)")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Maximum number of frames to extract (optional)")

    args = parser.parse_args()
    extract_frames(args.video, args.interval, args.output, args.max_frames)


if __name__ == "__main__":
    main()
