# 数据管理页 — 新增标签管理功能

## 一、Summary

在数据管理页新增"标签管理"功能，用于管理 YOLO 标注文件（.txt）。包含 4 项改动：
1. 视频媒体信息不再展示"已标注"字段（标注仅对图片有意义）
2. 左栏新增"标签管理"列表（展示已导入的 .txt 标签文件），与视频/图片列表并列
3. 图片的"已标注"状态改为**动态计算**：仅当标签管理中存在同名（by stem）的 .txt 文件时才显示"是"
4. 顶部按钮栏新增"导入标签"按钮，支持多选 .txt 文件导入到 `data/media/labels/`

## 二、Current State Analysis（基于 Phase 1 探索）

### 2.1 当前 UI 布局（[data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L56-L111)）

```
┌─────────────────────────────────────────────────────────────────┐
│ [导入视频] [导入图片] [扫描文件夹] [批量删除] [视频抽帧]         │
├──────────────┬──────────────────────────────┬──────────────────┤
│ 素材列表      │ 预览区                        │ 媒体信息          │
│              │                              │                  │
│ 视频素材      │  (图片/视频首帧)              │  文件名: ...     │
│ ┌──────────┐ │                              │  类型: ...       │
│ │001. a.mp4│ │                              │  路径: ...       │
│ └──────────┘ │                              │  大小: ...       │
│ 图片素材      │                              │  分辨率/帧率...  │
│ ┌──────────┐ │                              │  已标注: 是/否   │
│ │002. b.jpg│ │                              │  导入时间: ...   │
│ └──────────┘ │                              │                  │
├──────────────┴──────────────────────────────┴──────────────────┤
│ 共 N 个素材 | 视频: X | 图片: Y | 当前: 无选择                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 关键现状

| 位置 | 现状 | 问题 |
|------|------|------|
| [data_page.py:241-258](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L241-L258) `_show_info` | 视频/图片统一展示"已标注"字段 | 视频不应展示此字段 |
| [data_page.py:256](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L256) | `has_labels` 直接读 `m.has_labels` | 永远为 False（死字段） |
| [dataset_manager.py:23](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L23) | `MediaInfo.has_labels` 字段 | 3 处创建时硬编码 False，无更新逻辑 |
| [dataset_manager.py:151-183](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L151-L183) `import_images` | 图片存到 `data/media/images/` | 无标签导入方法 |
| registry JSON | 只有 `"media"` 一个 key | 无 `"labels"` section |
| 左栏布局 | 仅视频列表 + 图片列表 | 缺少标签列表 |

### 2.3 YOLO 标签命名约定（已确认）

- 标签文件为 `.txt`，与图片**同名不同扩展名**（如 `smoke_01.jpg` ↔ `smoke_01.txt`）
- 内容格式：`<class_id> <x_center> <y_center> <width> <height>`（归一化坐标）
- 类别：`configs/predefined_classes.txt` 仅 `smoke`（class_id=0）

## 三、Proposed Changes

### 修改 1：`dataset_manager.py` — 新增标签管理后端方法

**文件**：`e:\project\Dusc AI CV GPU\modules\dataset_manager.py`

**1a. 新增 `LabelInfo` dataclass**（放在 `MediaInfo` 之后，约第 25 行）：
```python
@dataclass
class LabelInfo:
    name: str           # 文件名，如 "smoke_01.txt"
    path: str           # 相对路径，如 "data/media/labels/smoke_01.txt"
    file_size: int
    line_count: int     # 标注行数（一个标注框一行）
    imported_at: datetime
```

**1b. 新增 `import_labels` 方法**（放在 `import_images` 之后，约第 184 行）：
```python
def import_labels(self, source_paths) -> list:
    """导入 YOLO 标签文件（.txt）到 data/media/labels/"""
    dest_dir = self.project_root / "data" / "media" / "labels"
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for sp in source_paths:
        sp = Path(sp)
        if sp.suffix.lower() != ".txt":
            continue
        dest_path = dest_dir / sp.name
        shutil.copy2(str(sp), str(dest_path))
        relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
        # 统计非空行数（标注框数）
        line_count = 0
        try:
            with open(dest_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        line_count += 1
        except Exception:
            line_count = 0
        entry = {
            "path": relative_path,
            "file_size": dest_path.stat().st_size,
            "line_count": line_count,
            "imported_at": datetime.now().isoformat(),
        }
        name = sp.name
        self._registry.setdefault("labels", {})[name] = entry
        results.append(LabelInfo(
            name=name, path=relative_path,
            file_size=entry["file_size"], line_count=line_count,
            imported_at=datetime.now(),
        ))
    self._save_registry()
    return results
```

**1c. 新增 `list_labels` 方法**（放在 `list_media` 之后，约第 356 行）：
```python
def list_labels(self):
    labels = self._registry.get("labels", {})
    result = []
    for name, entry in labels.items():
        result.append(LabelInfo(
            name=name,
            path=entry["path"],
            file_size=entry.get("file_size", 0),
            line_count=entry.get("line_count", 0),
            imported_at=datetime.fromisoformat(entry["imported_at"]) if isinstance(entry["imported_at"], str) else entry["imported_at"],
        ))
    return result
```

**1d. 新增 `remove_label` 方法**（放在 `remove_media` 之后，约第 375 行）：
```python
def remove_label(self, name, delete_file=False):
    labels = self._registry.get("labels", {})
    if name not in labels:
        return False
    entry = labels[name]
    if delete_file:
        raw_path = entry["path"]
        p = Path(raw_path)
        file_path = p if p.is_absolute() else self.project_root / p
        if file_path.exists():
            file_path.unlink()
    del labels[name]
    self._save_registry()
    return True
```

**1e. 新增 `has_label_for` 方法**（判断图片是否有对应标签，供 UI 调用）：
```python
def has_label_for(self, image_name):
    """检查图片是否有对应标签（按 stem 匹配，如 smoke_01.jpg ↔ smoke_01.txt）"""
    image_stem = Path(image_name).stem
    labels = self._registry.get("labels", {})
    return any(Path(name).stem == image_stem for name in labels.keys())
```

### 修改 2：`data_page.py` — UI 新增标签列表 + 导入标签按钮

**文件**：`e:\project\Dusc AI CV GPU\app\ui\data_page.py`

**2a. 顶部按钮栏新增"导入标签"按钮**（第 40 行后，`btn_import_image` 之后）：
```python
self.btn_import_label = QPushButton("导入标签")
self.btn_import_label.clicked.connect(self._on_import_label)
btn_row.addWidget(self.btn_import_label)
```

**2b. 左栏新增"标签管理"列表**（在 `image_list` 之后，约第 79 行）：
```python
# 标签管理区
left_layout.addWidget(QLabel("标签管理"))
self.label_list = QListWidget()
self.label_list.setSelectionMode(QAbstractItemView.SingleSelection)
self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
self.label_list.currentRowChanged.connect(self._on_label_selected)
self.label_list.customContextMenuRequested.connect(self._on_label_context_menu)
left_layout.addWidget(self.label_list, 1)
```

**2c. `_refresh_media` 方法扩展**：同时刷新标签列表
```python
# 在方法末尾、self.media_changed.emit() 之前添加
self.label_list.clear()
labels = self.dataset_manager.list_labels()
for lbl in labels:
    item = QListWidgetItem(lbl.name)
    item.setData(Qt.UserRole, lbl)
    self.label_list.addItem(item)
label_count = len(labels)
# 更新状态栏
self.status_label.setText(
    f"共 {total} 个素材 | 视频: {video_count} | 图片: {image_count} | 标签: {label_count} | 当前: 无选择"
)
```

**2d. 新增 `_on_label_selected` 方法**（放在 `_on_image_selected` 之后）：
```python
def _on_label_selected(self, row):
    if row < 0:
        return
    # 取消另外两个列表的选择
    self.video_list.setCurrentRow(-1)
    self.image_list.setCurrentRow(-1)
    item = self.label_list.item(row)
    if not item:
        return
    lbl = item.data(Qt.UserRole)
    self._current_media = None  # 标签不是 media
    self._current_label = lbl
    self._show_label_preview(lbl)
    self._show_label_info(lbl)
    self.status_label.setText(
        f"共 {self.video_list.count() + self.image_list.count()} 个素材 | "
        f"视频: {self.video_list.count()} | 图片: {self.image_list.count()} | "
        f"标签: {self.label_list.count()} | 当前: {lbl.name} (标签)"
    )
```

需在 `__init__` 中初始化 `self._current_label = None`。

**2e. 新增 `_show_label_preview` 方法**（标签预览：显示 txt 文本内容）：
```python
def _show_label_preview(self, lbl):
    path = self._resolve_media_path(lbl.path)
    if not path.exists():
        self.preview_label.setText(f"文件不存在:\n{path}")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # 限制显示长度，避免过长
        if len(content) > 2000:
            content = content[:2000] + "\n... (内容过长，已截断)"
        self.preview_label.setText(content)
    except Exception as e:
        self.preview_label.setText(f"无法读取标签:\n{str(e)}")
```

**2f. 新增 `_show_label_info` 方法**（右栏展示标签信息）：
```python
def _show_label_info(self, lbl):
    size_kb = lbl.file_size / 1024 if lbl.file_size else 0
    lines = [
        f"文件名: {lbl.name}",
        f"类型: 标签",
        f"路径: {lbl.path}",
        f"大小: {size_kb:.2f} KB",
        f"标注数: {lbl.line_count}",
        f"导入时间: {lbl.imported_at}",
    ]
    self.info_label.setText("\n".join(lines))
```

**2g. 修改 `_show_info` 方法**（第 241-258 行）：
- 视频：移除"已标注"字段
- 图片：`has_labels` 改为动态查询 `dataset_manager.has_label_for(m.name)`

```python
def _show_info(self, m):
    size_mb = m.file_size / (1024 * 1024) if m.file_size else 0
    lines = [
        f"文件名: {m.name}",
        f"类型: {'视频' if m.media_type == 'video' else '图片'}",
        f"路径: {m.path}",
        f"大小: {size_mb:.2f} MB",
    ]
    if m.media_type == "video":
        lines.extend([
            f"分辨率: {m.resolution}",
            f"帧率: {m.fps} FPS",
            f"帧数: {m.frame_count}",
            f"时长: {m.duration}s",
        ])
    else:  # 图片才显示已标注
        has_lbl = self.dataset_manager.has_label_for(m.name)
        lines.append(f"已标注: {'是' if has_lbl else '否'}")
    lines.append(f"导入时间: {m.imported_at}")
    self.info_label.setText("\n".join(lines))
```

**2h. 新增 `_on_import_label` 方法**（顶部按钮回调）：
```python
def _on_import_label(self):
    paths, _ = QFileDialog.getOpenFileNames(
        self, "选择标签文件", "", "标签文件 (*.txt)"
    )
    if not paths:
        return
    try:
        results = self.dataset_manager.import_labels(paths)
        self._refresh_media()
        QMessageBox.information(
            self, "导入成功",
            f"已导入 {len(results)} 个标签:\n" + "\n".join(r.name for r in results)
        )
    except Exception as e:
        QMessageBox.critical(self, "导入失败", f"导入标签失败:\n{str(e)}")
```

**2i. 新增 `_on_label_context_menu` 方法**（右键删除标签）：
```python
def _on_label_context_menu(self, pos):
    item = self.label_list.itemAt(pos)
    if not item:
        return
    menu = QMenu(self)
    delete_action = QAction("删除", self)
    delete_action.triggered.connect(self._on_delete_label)
    menu.addAction(delete_action)
    menu.exec_(self.label_list.viewport().mapToGlobal(pos))

def _on_delete_label(self):
    row = self.label_list.currentRow()
    if row < 0:
        return
    item = self.label_list.item(row)
    lbl = item.data(Qt.UserRole)
    reply = QMessageBox.question(
        self, "确认删除",
        f"确定要删除标签 \"{lbl.name}\" 吗？\n此操作将同时删除文件和登记记录。",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if reply != QMessageBox.Yes:
        return
    try:
        self.dataset_manager.remove_label(lbl.name, delete_file=True)
        self._refresh_media()
    except Exception as e:
        QMessageBox.critical(self, "删除失败", f"删除标签失败:\n{str(e)}")
```

**2j. 选择互斥更新**：`_on_video_selected` 和 `_on_image_selected` 中增加 `self.label_list.setCurrentRow(-1)`，实现三列表互斥选择。

### 修改 3：`dataset_manager.py` — registry 兼容性

`_load_registry` 无需修改（已有的 `self._registry = json.load(f)` 会自动加载新增的 `"labels"` key）。但需确保旧 registry（无 `"labels"` key）不报错：`list_labels` 中已用 `self._registry.get("labels", {})` 兼容。

## 四、目标界面布局

```
┌─────────────────────────────────────────────────────────────────────┐
│ [导入视频] [导入图片] [导入标签] [扫描文件夹] [批量删除] [视频抽帧]  │
├──────────────┬────────────────────────────────┬────────────────────┤
│ 素材列表      │ 预览区                          │ 媒体信息            │
│              │                                │                    │
│ 视频素材      │                                │  文件名: ...       │
│ ┌──────────┐ │   (图片/视频首帧/标签文本内容)   │  类型: ...         │
│ │001. a.mp4│ │                                │  路径: ...         │
│ │002. b.mp4│ │   例: 标签选中时显示            │  大小: ...         │
│ └──────────┘ │   0 0.327 0.332 0.311 0.303    │  分辨率/帧率...    │
│              │   0 0.510 0.621 0.244 0.198    │  已标注: 是/否     │ ← 仅图片显示
│ 图片素材      │                                │  导入时间: ...     │
│ ┌──────────┐ │                                │                    │
│ │003. c.jpg│ │                                │  (标签选中时显示)  │
│ │004. d.jpg│ │                                │  文件名: c.txt     │
│ └──────────┘ │                                │  类型: 标签        │
│              │                                │  标注数: 2         │
│ 标签管理      │                                │  ...               │
│ ┌──────────┐ │                                │                    │
│ │c.txt     │ │                                │                    │
│ │e.txt     │ │                                │                    │
│ └──────────┘ │                                │                    │
├──────────────┴────────────────────────────────┴────────────────────┤
│ 共 N 个素材 | 视频: X | 图片: Y | 标签: Z | 当前: 无选择            │
└─────────────────────────────────────────────────────────────────────┘
```

**布局说明：**
- 左栏：3 个列表垂直排列（视频素材 / 图片素材 / 标签管理），各占 stretch=1
- 三列表**互斥选择**：选中任一项，其他两表自动取消选择
- 标签列表不参与统一编号（无 `001.` 前缀），仅显示文件名，避免与素材批量删除编号混淆
- 标签列表有自己的右键菜单（仅"删除"单项），不纳入"批量删除"范围
- 预览区根据选中类型切换：图片→图像，视频→首帧，标签→txt 文本内容
- 右栏"已标注"字段：视频不显示，图片显示（动态查询标签注册表）

## 五、Assumptions & Decisions

1. **标签存储路径**：`data/media/labels/`（与 `data/media/images/` 对称，类比图片导入逻辑）。
2. **标签注册表**：在 registry JSON 新增独立 `"labels"` section，与 `"media"` 分离，避免污染 `list_media()`。结构：`{"media": {...}, "labels": {name: {path, file_size, line_count, imported_at}}}`。
3. **has_labels 动态计算**：不在 registry 中存储，改为 `_show_info` 时调用 `dataset_manager.has_label_for(name)` 实时查询。按 stem 匹配（`smoke_01.jpg` ↔ `smoke_01.txt`），保持准确。
4. **视频不显示"已标注"**：`_show_info` 中仅图片分支追加该字段。
5. **标签列表不编号**：标签不参与视频/图片的统一编号，仅显示文件名。批量删除仍只针对视频+图片。
6. **标签删除**：仅支持右键单项删除（带二次确认），不纳入批量删除。
7. **标签预览**：选中标签时，预览区显示 txt 文件文本内容（前 2000 字符，超出截断）。
8. **扫描文件夹不扫描标签**：保持现有 `scan_media_dir` 只扫描视频+图片，标签仅通过"导入标签"按钮导入（避免范围蔓延）。
9. **向后兼容**：旧 registry 无 `"labels"` key 时，`list_labels` 返回空列表，`has_label_for` 返回 False，不报错。
10. **LabelInfo 不复用 MediaInfo**：标签字段集不同（无 duration/fps/resolution），独立 dataclass 更清晰。

## 六、Verification Steps

### 6.1 静态验证
1. 启动应用，确认顶部按钮栏出现"导入标签"按钮（顺序：导入视频|导入图片|导入标签|扫描文件夹|批量删除|视频抽帧）。
2. 确认左栏出现"标签管理"列表区，状态栏新增"标签: 0"字段。
3. 无素材/标签时三个列表均为空，无报错。

### 6.2 导入标签验证
1. 准备测试图片 `smoke_01.jpg` 和标签 `smoke_01.txt`（内容如 `0 0.327 0.332 0.311 0.303`）。
2. 点击"导入图片"导入 `smoke_01.jpg`，确认图片列表出现该项。
3. 点击"导入标签"导入 `smoke_01.txt`，确认标签列表出现该项，状态栏"标签: 1"。
4. 选中 `smoke_01.jpg`，确认右栏"已标注: 是"（验证动态匹配）。
5. 选中 `smoke_01.txt`，确认预览区显示 `0 0.327 0.332 0.311 0.303`，右栏显示"类型: 标签"、"标注数: 1"。

### 6.3 视频信息验证
1. 选中视频素材，确认右栏**不显示**"已标注"字段（仅显示文件名/类型/路径/大小/分辨率/帧率/帧数/时长/导入时间）。

### 6.4 互斥选择验证
1. 选中视频→图片列表和标签列表均取消选择。
2. 选中图片→视频列表和标签列表均取消选择。
3. 选中标签→视频列表和图片列表均取消选择。

### 6.5 删除标签验证
1. 右键标签→删除→确认，标签从列表消失。
2. 删除标签后，对应图片的"已标注"状态应变为"否"（验证动态查询）。

### 6.6 回归验证
1. "导入视频"、"导入图片"、"扫描文件夹"、"批量删除"、"视频抽帧"功能不受影响。
2. 旧 registry（无 labels key）加载不报错，标签列表为空。
