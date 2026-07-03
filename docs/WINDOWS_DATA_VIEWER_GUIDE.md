# Windows 端数据查看指南

> 本文档说明如何从 Jetson Nano 拉取检测数据（SQLite 数据库 + 视频片段）到 Windows 端查看分析。

## 前置条件

- Nano 与 Windows 在同一局域网
- Nano 的 SSH 已开启（默认端口 22）
- 知道 Nano 的 IP 地址（例如 `192.168.1.100`）和用户名（通常 `jetson`）

---

## 1. 拉取数据库文件

### 1.1 单次拉取

在 Windows PowerShell 或 CMD 执行：

```bash
# 拉取 events.db 到当前目录
scp jetson@<nano-ip>:~/smoke_data/events.db .

# 例如
scp jetson@192.168.1.100:~/smoke_data/events.db .
```

### 1.2 拉取视频文件

```bash
# 拉取单个视频
scp jetson@<nano-ip>:~/smoke_data/videos/20260701_10.avi .

# 拉取所有视频（整个目录）
scp -r jetson@<nano-ip>:~/smoke_data/videos ./videos_backup
```

### 1.3 拉取全部数据

```bash
# 拉取整个 smoke_data 目录
scp -r jetson@<nano-ip>:~/smoke_data ./smoke_data_backup
```

---

## 2. 使用 DB Browser for SQLite 查询

### 2.1 安装 DB Browser

下载地址：https://sqlitebrowser.org/dl/

选择 Windows 64-bit 版本，安装后打开。

### 2.2 打开数据库

1. 启动 DB Browser for SQLite
2. 点击"打开数据库"
3. 选择刚拉取的 `events.db` 文件

### 2.3 浏览数据

- **浏览数据** 标签页：可查看 `events` 和 `stats_hourly` 两张表
- **执行 SQL** 标签页：运行查询

### 2.4 常用 SQL 查询示例

#### 查询最近 100 条检测事件

```sql
SELECT id, ts, class, conf, area_pct, level, video_path, inference_ms
FROM events
ORDER BY ts DESC
LIMIT 100;
```

#### 查询所有 HEAVY 等级事件

```sql
SELECT ts, class, conf, area_pct, video_path
FROM events
WHERE level = 'HEAVY'
ORDER BY ts DESC;
```

#### 按小时统计检测数

```sql
SELECT
    substr(ts, 1, 13) AS hour,
    COUNT(*) AS total,
    SUM(CASE WHEN class LIKE '%smoke%' THEN 1 ELSE 0 END) AS smoke_count,
    MAX(conf) AS max_conf,
    MAX(area_pct) AS max_area
FROM events
GROUP BY hour
ORDER BY hour DESC;
```

#### 查询高置信度事件（>0.7）

```sql
SELECT ts, class, conf, area_pct, level, video_path
FROM events
WHERE conf > 0.7
ORDER BY conf DESC;
```

#### 查询某天的所有事件

```sql
SELECT ts, class, conf, level, video_path
FROM events
WHERE ts LIKE '2026-07-01%'
ORDER BY ts;
```

#### 查看小时统计表

```sql
SELECT hour, total_events, smoke_events, max_conf, max_area, max_level, avg_inference_ms
FROM stats_hourly
ORDER BY hour DESC;
```

#### 导出查询结果为 CSV

在 DB Browser 中执行 SQL 后：
1. 点击"导出"或右键结果 → "导出为 CSV"
2. 保存到本地，可用 Excel 打开分析

---

## 3. 视频文件查看

拉取的 `.avi` 视频文件可用以下播放器打开：

- **VLC 播放器**（推荐，支持 XVID 编码）：https://www.videolan.org/
- Windows Media Player（可能需要安装 XVID 编解码器）
- PotPlayer、MPC-HC 等

视频内容包含：
- 检测框（红色=smoke、橙色=fire、青色=default）
- 标签（类别 + 置信度 + 面积占比）
- 左上角 HUD（等级、推理耗时、FPS、烟雾状态）

文件命名规则：`YYYYMMDD_HH.avi`（如 `20260701_10.avi` 表示 7 月 1 日 10 点的录像）

---

## 4. 自动化拉取脚本（可选）

如果需要定期自动拉取，可创建以下批处理脚本：

### `pull_data.bat`

```batch
@echo off
set NANO_IP=192.168.1.100
set NANO_USER=jetson
set LOCAL_DIR=%USERPROFILE%\Desktop\smoke_data

echo === 拉取 Nano 检测数据 ===
echo Nano: %NANO_USER%@%NANO_IP%
echo 本地目录: %LOCAL_DIR%

mkdir "%LOCAL_DIR%" 2>nul
mkdir "%LOCAL_DIR%\videos" 2>nul

echo.
echo [1/2] 拉取数据库...
scp %NANO_USER%@%NANO_IP%:~/smoke_data/events.db "%LOCAL_DIR%\"

echo.
echo [2/2] 拉取视频文件（最近24小时）...
scp %NANO_USER%@%NANO_IP%:~/smoke_data/videos/*.avi "%LOCAL_DIR%\videos\"

echo.
echo 完成！数据保存在: %LOCAL_DIR%
echo 可以用 DB Browser for SQLite 打开 %LOCAL_DIR%\events.db
pause
```

使用方法：
1. 修改 `NANO_IP` 为您的 Nano IP
2. 保存为 `pull_data.bat`
3. 双击运行

---

## 5. 数据目录结构

Nano 端：

```
~/smoke_data/
├── events.db              # SQLite 数据库
└── videos/
    ├── 20260701_10.avi    # 7月1日 10点录像
    ├── 20260701_11.avi    # 7月1日 11点录像
    └── ...
```

Windows 拉取后：

```
smoke_data_backup/
├── events.db
└── videos/
    └── *.avi
```

---

## 6. 常见问题

### Q: scp 连接超时？

检查：
1. Nano 是否开机且在同一网络
2. Nano 的 SSH 服务是否运行：`sudo systemctl status ssh`
3. 防火墙是否阻止 22 端口

### Q: 视频文件无法播放？

- 确认用 VLC 播放器
- 如果文件为 0 字节，说明 VideoWriter 初始化失败，检查 Nano 上的 OpenCV 是否支持 XVID

### Q: 数据库打开失败？

- 确认文件已完整拉取（文件大小 > 0）
- 如果 Nano 上的 smoke_detect.py 正在运行，数据库可能被锁定，建议先停止再拉取

### Q: 如何查看 Nano 上的数据不拉取？

SSH 登录 Nano 后用 sqlite3 命令行：

```bash
ssh jetson@<nano-ip>
sqlite3 ~/smoke_data/events.db
sqlite> SELECT COUNT(*) FROM events;
sqlite> SELECT * FROM events ORDER BY ts DESC LIMIT 10;
sqlite> .quit
```
