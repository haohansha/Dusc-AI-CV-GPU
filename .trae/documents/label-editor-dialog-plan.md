# 内置标签标注窗口（添加标签按钮）

## Summary

在数据管理页顶部按钮栏新增"**添加标签**"按钮，点击后弹出一个**内置的标注窗口**（类似 labelImg），支持鼠标拉框 + 手动输入坐标两种方式给图片添加 YOLO 格式标签，并能浏览/编辑/删除已有标签。批准后实现并接入按钮。

## Current State Analysis

### 现有架构（基于 Phase 1 探索）

- **DataPage** ([app/ui/data_page.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py))：数据管理页，顶部按钮栏含 6 个按钮（导入视频/图片/标签、扫描文件夹、批量删除、视频抽帧）。左栏三列表（视频/图片/标签），中栏预览，右栏媒体信息。
- **DatasetManager** ([modules/dataset_manager.py](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py))：已有 `import_labels` / `list_labels` / `remove_label` / `has_label_for` 四个方法。标签存 `resource/labels/<stem>.txt`，YOLO 格式 `<class_id> <xc> <yc> <w> <h>`（归一化）。
- **类别文件** [configs/predefined_classes.txt](file:///e:/project/Dusc%20AI%20CV%20GPU/configs/predefined_classes.txt)：当前只有 `smoke` 一行。
- **MainWindow** ([app/main_window.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/main_window.py))：DataPage 实例化为 `self.tab_data`，传入 `project_root` 和 `dataset_manager`。
- **既有外部方案**：`labelimg.bat` 调外部 labelImg 库——本次要做**内置**窗口替代它，无需外部依赖。

### 标签格式约定

- YOLO 归一化坐标：`<class_id> <x_center> <y_center> <width> <height>`，均为 0~1 浮点
- 文件命名：与图片同 stem，如 `smoke_01.jpg` ↔ `smoke_01.txt`
- 一个标注框占一行

## Proposed Changes

### 改动 1：新增 `app/ui/label_editor_dialog.py`（核心新文件）

新增 `LabelEditorDialog(QDialog)` 类，模态对话框。布局如下：

```
┌─────────────────────────────────────────────────────────────┐
│ 标注编辑器                                          [×]      │
├──────────┬──────────────────────────────────┬───────────────┤
│ 图片列表  │        画布区（自定义 QWidget）   │ 标注框列表    │
│ ┌──────┐ │                                  │ ┌───────────┐ │
│ │001.  │ │     [显示当前图片，支持鼠标拉框]  │ │class  box │ │
│ │002.  │ │                                  │ │0      □   │ │
│ │003.  │ │                                  │ │0      □   │ │
│ │ ...  │ │                                  │ │           │ │
│ └──────┘ │                                  │ └───────────┘ │
│          │                                  │ [删除选中]    │
│ [上一张]  │                                  │ [清空全部]    │
│ [下一张]  │                                  │               │
│          ├──────────────────────────────────┤               │
│          │ 手动输入区（QGroupBox）           │               │
│          │ 类别: [smoke ▼]                  │               │
│          │ xc: [____] yc: [____]            │               │
│          │ w:  [____] h:  [____]            │               │
│          │ [添加]                           │               │
├──────────┴──────────────────────────────────┴───────────────┤
│ 状态: smoke_01.jpg | 1920x1080 | 已标注 3 框 | 第 2/15 张   │
├─────────────────────────────────────────────────────────────┤
│              [保存当前] [保存全部并关闭] [取消]              │
└─────────────────────────────────────────────────────────────┘
```

#### 关键组件设计

**1. `AnnotationCanvas(QWidget)` —— 内部类，画布**

- 重写 `paintEvent`：绘制图片 + 已有标注框（红框 + 类别文字）+ 当前正在拉的虚线框
- 重写 `mousePressEvent`：记录拉框起点
- 重写 `mouseMoveEvent`：更新虚线框，状态栏实时显示像素坐标
- 重写 `mouseReleaseEvent`：拉框完成 → 转归一化坐标 → 弹类别选择 → 加入列表
- 内部状态：`_image_path`、`_boxes`（list of (class_id, xc, yc, w, h)）、`_drawing`、`_start_point`、`_current_box`

**2. 图片列表（左栏 `QListWidget`）**

- 从 `dataset_manager.list_media()` 取所有 `media_type == "image"` 的图片
- 显示统一编号 `001. <name>`，与 DataPage 一致
- 切换图片时：先保存当前图片标签 → 加载新图片及其标签到画布

**3. 标注框列表（右栏 `QListWidget`）**

- 每行：`<class_name>  xc=0.123 yc=0.456 w=0.789 h=0.012`
- 选中时画布上对应框高亮（蓝色加粗）
- 右键菜单 / 删除按钮：删除选中框
- 清空全部：清空当前图片所有框

**4. 手动输入区（QGroupBox）**

- 类别下拉：从 `configs/predefined_classes.txt` 读取
- 4 个 `QDoubleSpinBox`（0.000~1.000，步长 0.001）：xc / yc / w / h
- "添加"按钮：校验后加入标注框列表

**5. 底部按钮**

- 保存当前：写入 `resource/labels/<当前图片stem>.txt`，并更新 registry
- 保存全部并关闭：遍历所有已修改图片逐个保存 → `accept()`
- 取消：`reject()`（不保存未保存的改动，需确认弹窗）

#### 与 DatasetManager 的交互

新增 `DatasetManager` 方法 `save_label_for_image(image_name, boxes)`：
- 接收 `boxes`（list of (class_id, xc, yc, w, h)）
- 写入 `resource/labels/<stem>.txt`
- 更新 registry 的 `labels` section（若已存在则覆盖）
- 复用 `import_labels` 的 line_count 统计逻辑

#### 类别管理决策

**固定读取 `configs/predefined_classes.txt`**，不在窗口内增删类别。理由：
- 烟雾检测项目当前只有 `smoke` 单类别
- 简化 UI，避免引入类别冲突
- 如需新增类别，用户可直接编辑 txt 文件

#### 窗口类型决策

**模态 QDialog**。理由：
- 标注是专注操作，模态避免用户误操作主窗口导致数据不一致
- 实现简单，关闭时自动释放资源
- 主窗口在背后仍可见，用户可参考

### 改动 2：`app/ui/data_page.py` —— 加按钮 + 接入

#### 改动 2a：导入 LabelEditorDialog

文件顶部新增：
```python
from app.ui.label_editor_dialog import LabelEditorDialog
```

#### 改动 2b：顶部按钮栏新增"添加标签"按钮

在 [data_page.py#L55-L57](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L55-L57) "视频抽帧"按钮**之后**插入：
```python
self.btn_extract = QPushButton("视频抽帧")
self.btn_extract.clicked.connect(self._on_extract_frames)
btn_row.addWidget(self.btn_extract)

self.btn_annotate = QPushButton("添加标签")  # 新增
self.btn_annotate.clicked.connect(self._on_annotate)
btn_row.addWidget(self.btn_annotate)
```

#### 改动 2c：新增 `_on_annotate` 方法

```python
def _on_annotate(self):
    """打开标签标注窗口"""
    images = [m for m in self.dataset_manager.list_media() if m.media_type == "image"]
    if not images:
        QMessageBox.warning(self, "提示", "当前没有图片素材可标注，请先导入图片或抽帧")
        return
    dialog = LabelEditorDialog(self.project_root, self.dataset_manager, self)
    if dialog.exec_() == QDialog.Accepted:
        self._refresh_media()  # 标签变更后刷新列表和"已标注"状态
```

### 改动 3：`modules/dataset_manager.py` —— 新增 save_label_for_image 方法

在 `import_labels` 之后新增：
```python
def save_label_for_image(self, image_name, boxes):
    """保存图片的标签到 resource/labels/<stem>.txt，覆盖原有内容

    Args:
        image_name: 图片文件名，如 "smoke_01.jpg"
        boxes: list of (class_id, xc, yc, w, h) 归一化坐标
    Returns:
        LabelInfo
    """
    stem = Path(image_name).stem
    dest_dir = self.resource_dir / "labels"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{stem}.txt"

    # 写入 YOLO 格式
    with open(dest_path, "w", encoding="utf-8") as f:
        for cid, xc, yc, w, h in boxes:
            f.write(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")

    relative_path = str(dest_path.relative_to(self.project_root)).replace("\\", "/")
    line_count = len(boxes)
    entry = {
        "path": relative_path,
        "file_size": dest_path.stat().st_size,
        "line_count": line_count,
        "imported_at": datetime.now().isoformat(),
    }
    name = f"{stem}.txt"
    self._registry.setdefault("labels", {})[name] = entry
    self._save_registry()
    return LabelInfo(
        name=name, path=relative_path,
        file_size=entry["file_size"], line_count=line_count,
        imported_at=datetime.now(),
    )
```

## Assumptions & Decisions

1. **窗口类型**：模态 `QDialog`——专注标注，避免主窗口误操作。
2. **类别管理**：固定读 `configs/predefined_classes.txt`，窗口内不可编辑类别。
3. **拉框坐标**：鼠标拉框时状态栏实时显示**像素坐标**，标注框列表显示**归一化坐标**（与 YOLO 格式一致）。
4. **保存策略**：切换图片时自动保存当前图片；底部"保存当前"显式保存；"保存全部并关闭"批量保存所有已修改图片。
5. **未保存退出**：若有未保存改动，点取消时弹确认框（"有未保存的标注，确认退出？"）。
6. **图片缩放**：画布按图片原始尺寸显示，若超出窗口则用 `QScrollArea` 包裹可滚动；拉框坐标按图片原始像素计算，再归一化。
7. **类别显示**：标注框旁显示类别名（如 `smoke`）而非 class_id，更直观。
8. **空标签文件**：若 `boxes` 为空列表，仍写入空 txt 文件（表示该图片无标注），registry 中 line_count=0。
9. **不删除原文件**：`save_label_for_image` 直接覆盖写入，不调用 `remove_label`。
10. **不引入新依赖**：仅用 PyQt5 已有组件（QWidget/QPainter/QPixmap），无需 pip 安装。

## Verification Steps

1. **语法检查**：
   ```
   python -m py_compile app/ui/label_editor_dialog.py
   python -m py_compile app/ui/data_page.py
   python -m py_compile modules/dataset_manager.py
   ```
2. **按钮接入**：启动 `run.bat` → 切到"数据管理"页 → 顶部应出现"添加标签"按钮（第 7 个）。
3. **空图片提示**：无图片素材时点按钮 → 弹"当前没有图片素材可标注"。
4. **窗口打开**：有图片素材时点按钮 → 弹出标注窗口，左栏列出所有图片，画布显示第一张。
5. **鼠标拉框**：在画布上拖拽 → 实时显示虚线框 → 松开后弹类别选择（默认 smoke）→ 框加入右栏列表 → 画布显示红框 + `smoke` 文字。
6. **手动输入**：在手动输入区填 xc/yc/w/h → 点"添加" → 框加入列表 → 画布同步显示。
7. **删除标注**：右栏选中一行 → 点"删除选中" → 画布红框消失。
8. **切换图片**：点左栏另一张图 → 当前图自动保存 → 新图加载（含已有标注）。
9. **保存验证**：关闭窗口后 → DataPage 标签列表新增/更新对应 .txt → 图片右栏"已标注: 是"。
10. **文件验证**：用文本编辑器打开 `resource/labels/<stem>.txt` → 内容为 `<class_id> <xc> <yc> <w> <h>` 格式，每行一框。
11. **已有标签加载**：对已有 .txt 的图片打开窗口 → 画布应显示原有红框，右栏列表显示原有标注。

## 实施顺序（批准后执行）

1. 新增 `app/ui/label_editor_dialog.py`（AnnotationCanvas + LabelEditorDialog）
2. `modules/dataset_manager.py` 新增 `save_label_for_image` 方法
3. `app/ui/data_page.py` 加按钮 + 导入 + `_on_annotate` 方法
4. 三个文件语法检查
5. 运行 GUI 验证
