#!/usr/bin/env python3
"""清理脚本：删除 N 天前的检测事件、统计和视频文件

用法：
    python3 cleanup.py                  # 默认清理 3 天前
    python3 cleanup.py --days 7         # 清理 7 天前
    python3 cleanup.py --dry-run        # 只查看不删除

建议用 cron 每天凌晨 1 点运行：
    0 1 * * * /usr/bin/python3 /path/to/cleanup.py >> /tmp/cleanup.log 2>&1
"""
import argparse
import sys
from pathlib import Path

# 添加 modules 路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "modules"))

from data_storage import DataStorage


def main():
    parser = argparse.ArgumentParser(description="清理旧的检测数据")
    parser.add_argument("--days", type=int, default=3, help="保留天数（默认 3）")
    parser.add_argument("--data-dir", default=str(Path.home() / "smoke_data"),
                        help="数据目录（默认 ~/smoke_data）")
    parser.add_argument("--dry-run", action="store_true", help="只查看不删除")
    args = parser.parse_args()

    print(f"=== Cleanup ===")
    print(f"Data dir: {args.data_dir}")
    print(f"Keep days: {args.days}")
    print(f"Dry run: {args.dry_run}")

    storage = DataStorage(base_dir=Path(args.data_dir))

    if args.dry_run:
        # 只查询不删除
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=args.days)).isoformat(timespec="seconds")
        cur = storage.conn.execute("SELECT COUNT(*) FROM events WHERE ts < ?", (cutoff,))
        old_events = cur.fetchone()[0]
        cutoff_hour = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%dT%H")
        cur = storage.conn.execute("SELECT COUNT(*) FROM stats_hourly WHERE hour < ?", (cutoff_hour,))
        old_stats = cur.fetchone()[0]
        old_videos = 0
        freed_mb = 0
        from datetime import datetime as dt
        for v in storage.videos_dir.glob("*.avi"):
            mtime = dt.fromtimestamp(v.stat().st_mtime)
            if mtime < (datetime.now() - timedelta(days=args.days)):
                old_videos += 1
                freed_mb += v.stat().st_size / 1024 / 1024
        for v in storage.videos_dir.glob("*.mp4"):
            mtime = dt.fromtimestamp(v.stat().st_mtime)
            if mtime < (datetime.now() - timedelta(days=args.days)):
                old_videos += 1
                freed_mb += v.stat().st_size / 1024 / 1024
        print(f"\n[Dry Run] Would delete:")
        print(f"  Events: {old_events}")
        print(f"  Stats:  {old_stats}")
        print(f"  Videos: {old_videos} ({freed_mb:.2f} MB)")
    else:
        result = storage.cleanup_old(days=args.days)
        print(f"\nDeleted:")
        print(f"  Events: {result['deleted_events']}")
        print(f"  Stats:  {result['deleted_stats']}")
        print(f"  Videos: {result['deleted_videos']} ({result['freed_mb']:.2f} MB)")

    storage.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
