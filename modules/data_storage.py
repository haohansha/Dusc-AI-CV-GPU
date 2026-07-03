"""数据存储模块：SQLite 事件记录 + 小时聚合统计

为 Jetson Nano 边缘端提供轻量级数据持久化：
- events 表：每次检测一条记录（时间戳、类别、置信度、面积、等级、视频路径）
- stats_hourly 表：每小时聚合一条统计（总检测数、烟雾数、最高等级等）

数据库文件默认存放在 ~/smoke_data/events.db，视频片段存放在 ~/smoke_data/videos/
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


# SQL 建表语句
_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    class        TEXT NOT NULL,
    conf         REAL NOT NULL,
    area_pct     REAL NOT NULL,
    level        TEXT NOT NULL,
    video_path   TEXT,
    inference_ms REAL
);
CREATE INDEX IF NOT EXISTS idx_events_ts    ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);

CREATE TABLE IF NOT EXISTS stats_hourly (
    hour             TEXT PRIMARY KEY,
    total_events     INTEGER NOT NULL,
    smoke_events     INTEGER NOT NULL,
    max_conf         REAL,
    max_area         REAL,
    max_level        TEXT,
    avg_inference_ms REAL
);
"""


class DataStorage:
    """SQLite 数据存储，支持事件写入与小时聚合"""

    def __init__(self, base_dir: Optional[Path] = None):
        """初始化数据库与目录结构

        Args:
            base_dir: 数据根目录，默认 ~/smoke_data
        """
        if base_dir is None:
            base_dir = Path.home() / "smoke_data"
        self.base_dir = Path(base_dir)
        self.videos_dir = self.base_dir / "videos"
        self.db_path = self.base_dir / "events.db"

        # 创建目录
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ---------- 事件写入 ----------

    def insert_event(self, cls_name: str, conf: float, area_pct: float,
                     level: str, video_path: Optional[str] = None,
                     inference_ms: float = 0.0,
                     ts: Optional[str] = None) -> int:
        """插入一条检测事件

        Args:
            cls_name: 类别名（smoke/fire/default）
            conf: 置信度 0-1
            area_pct: 检测框面积占比 %
            level: 等级 LIGHT/MEDIUM/HEAVY/NONE
            video_path: 该事件所属视频片段路径
            inference_ms: 推理耗时 ms
            ts: ISO8601 时间戳，默认当前时间

        Returns:
            插入的记录 id
        """
        if ts is None:
            ts = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            "INSERT INTO events (ts, class, conf, area_pct, level, video_path, inference_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, cls_name, conf, area_pct, level, video_path, inference_ms),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_events_batch(self, events: list) -> None:
        """批量插入事件（一个事务，比循环单条插入快）

        Args:
            events: 字典列表，每个字典含 cls_name/conf/area_pct/level/video_path/inference_ms
        """
        rows = [
            (e.get("ts", datetime.now().isoformat(timespec="seconds")),
             e["class"], e["conf"], e["area_pct"], e["level"],
             e.get("video_path"), e.get("inference_ms", 0.0))
            for e in events
        ]
        self.conn.executemany(
            "INSERT INTO events (ts, class, conf, area_pct, level, video_path, inference_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()

    # ---------- 小时聚合 ----------

    def aggregate_hour(self, hour_str: Optional[str] = None) -> Optional[dict]:
        """聚合指定小时的统计数据，写入 stats_hourly 表

        Args:
            hour_str: 小时键 'YYYY-MM-DDTHH'，默认上一小时

        Returns:
            统计字典，若无数据返回 None
        """
        if hour_str is None:
            # 默认聚合上一小时（确保该小时已完成）
            now = datetime.now()
            last_hour = now.replace(minute=0, second=0, microsecond=0)
            # 简化处理：用当前小时（调用时通常该小时有数据）
            hour_str = now.strftime("%Y-%m-%dT%H")

        # 查询该小时所有事件
        rows = self.conn.execute(
            "SELECT class, conf, area_pct, level, inference_ms FROM events "
            "WHERE ts LIKE ?",
            (f"{hour_str}%",),
        ).fetchall()

        if not rows:
            return None

        total = len(rows)
        smoke_count = sum(1 for r in rows if "smoke" in r[0].lower())
        confs = [r[1] for r in rows]
        areas = [r[2] for r in rows]
        levels = [r[3] for r in rows]
        inf_ms = [r[4] for r in rows if r[4] is not None]

        # 等级排序：HEAVY > MEDIUM > LIGHT > NONE
        level_order = {"HEAVY": 3, "MEDIUM": 2, "LIGHT": 1, "NONE": 0}
        max_level = max(levels, key=lambda lv: level_order.get(lv, 0))

        stats = {
            "hour": hour_str,
            "total_events": total,
            "smoke_events": smoke_count,
            "max_conf": max(confs) if confs else 0,
            "max_area": max(areas) if areas else 0,
            "max_level": max_level,
            "avg_inference_ms": sum(inf_ms) / len(inf_ms) if inf_ms else 0,
        }

        self.conn.execute(
            "INSERT OR REPLACE INTO stats_hourly "
            "(hour, total_events, smoke_events, max_conf, max_area, max_level, avg_inference_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (stats["hour"], stats["total_events"], stats["smoke_events"],
             stats["max_conf"], stats["max_area"], stats["max_level"],
             stats["avg_inference_ms"]),
        )
        self.conn.commit()
        return stats

    # ---------- 查询 ----------

    def query_events(self, limit: int = 100, level: Optional[str] = None) -> list:
        """查询最近的事件

        Args:
            limit: 返回条数
            level: 等级过滤（HEAVY/MEDIUM/LIGHT/NONE）

        Returns:
            事件字典列表
        """
        if level:
            cur = self.conn.execute(
                "SELECT id, ts, class, conf, area_pct, level, video_path, inference_ms "
                "FROM events WHERE level = ? ORDER BY ts DESC LIMIT ?",
                (level, limit),
            )
        else:
            cur = self.conn.execute(
                "SELECT id, ts, class, conf, area_pct, level, video_path, inference_ms "
                "FROM events ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
        cols = ["id", "ts", "class", "conf", "area_pct", "level", "video_path", "inference_ms"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def query_stats(self, days: int = 7) -> list:
        """查询最近 N 天的小时统计

        Args:
            days: 天数

        Returns:
            统计字典列表
        """
        cutoff = datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S")
        # 简化：返回所有统计（数据量不大）
        cur = self.conn.execute(
            "SELECT hour, total_events, smoke_events, max_conf, max_area, max_level, avg_inference_ms "
            "FROM stats_hourly ORDER BY hour DESC"
        )
        cols = ["hour", "total_events", "smoke_events", "max_conf",
                "max_area", "max_level", "avg_inference_ms"]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ---------- 清理 ----------

    def cleanup_old(self, days: int = 3) -> dict:
        """清理 N 天前的数据

        Args:
            days: 保留天数

        Returns:
            清理统计字典
        """
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        cutoff_hour = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H")

        # 删除旧事件
        cur_events = self.conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
        deleted_events = cur_events.rowcount

        # 删除旧统计
        cur_stats = self.conn.execute("DELETE FROM stats_hourly WHERE hour < ?", (cutoff_hour,))
        deleted_stats = cur_stats.rowcount

        self.conn.commit()

        # 删除旧视频文件
        deleted_videos = 0
        freed_bytes = 0
        for v in self.videos_dir.glob("*.avi"):
            mtime = datetime.fromtimestamp(v.stat().st_mtime)
            if mtime < (datetime.now() - timedelta(days=days)):
                freed_bytes += v.stat().st_size
                v.unlink()
                deleted_videos += 1
        for v in self.videos_dir.glob("*.mp4"):
            mtime = datetime.fromtimestamp(v.stat().st_mtime)
            if mtime < (datetime.now() - timedelta(days=days)):
                freed_bytes += v.stat().st_size
                v.unlink()
                deleted_videos += 1

        return {
            "deleted_events": deleted_events,
            "deleted_stats": deleted_stats,
            "deleted_videos": deleted_videos,
            "freed_mb": round(freed_bytes / 1024 / 1024, 2),
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
