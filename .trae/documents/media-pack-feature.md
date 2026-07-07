# 素材打包功能规划

## 概述

在数据管理页"添加标签"按钮后新增"素材打包"按钮，打开独立的分类管理对话框。用户可自定义分类（如"微调用"、"测试用"），将**已标注的图片素材**归入一个或多个分类，便于后续训练时按分类批量选择素材。已归类的素材在媒体信息区显示分类归属。

## 当前状态分析

### 现有结构（基于代码探索）

- **顶部按钮栏** [app/ui/data_page.py:36-66](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L36-L66)：7 个按钮末尾是"添加标签"，通过 `addStretch()` 推到左侧。
- **媒体信息区** [app/ui/data_page.py:117-128, 298-317](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L298-L317)：单个 `QLabel`，用 `lines.append()` 拼接文本展示。
- **media_registry.json 结构**：`media` section 每条目 9 字段（path/type/duration/resolution/fps/frame_count/file_size/imported_at/has_labels），**无任何分类字段**。
- **MediaInfo dataclass** [modules/dataset_manager.py:12-23](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L12-L23)：无 categories 字段。
- **_entry_to_mediainfo** [modules/dataset_manager.py:592-604](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L592-L604)：从 registry dict 转 dataclass。
- **_load_registry / _save_registry** [modules/dataset_manager.py:44-54](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L44-L54)：JSON 读写，已有 mkdir + ensure_ascii=False。
- **has_label_for** [modules/dataset_manager.py:586-590](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L586-L590)：按 stem 匹配 .txt 是否存在，用于判断图片是否已标注。
- **_on_annotate** [app/ui/data_page.py:621-630](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L621-L630)：LabelEditorDialog 的调用范例。

### 关键约束

- 只对**已标注的图片素材**开放归类（无标签的图片不参与打包，避免无意义数据进入训练集）。
- 同一素材可属于多个分类（多对多关系）。
- 分类名用户可自定义，支持新建/重命名/删除。
- 复用现有 `_save_registry()` 持久化机制，不引入新文件。

## 设计决策

1. **存储方式**：扩展 `media_registry.json`
   - 在每个 media 条目新增 `categories: list[str]` 字段（默认 `[]`）。
   - 在 registry 顶层新增 `categories` section，存储分类定义列表 `{"categories": ["微调用", "测试用", ...]}`。
   - 优势：复用现有读写机制，事务一致性强，不引入新文件。

2. **窗口交互**：双栏分类管理器（独立 QDialog）
   - 左栏：已标注图片素材列表（QListWidget，支持多选）。
   - 右栏：分类列表（QListWidget）+ 新建/重命名/删除按钮。
   - 操作方式：选中左栏素材 → 勾选右栏分类前的 QCheckBox → 实时保存。
   - 优势：直观清晰，一屏可见素材与分类的归属关系。

3. **UI 入口**：在"添加标签"按钮后新增"素材打包"按钮，参照 `btn_annotate` 的连接方式。

## 实施步骤

### 步骤 1：扩展数据层（modules/dataset_manager.py）

**1.1 MediaInfo dataclass 加字段** [L12-23](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L12-L23)

```python
@dataclass
class MediaInfo:
    name: str
    path: str
    media_type: str
    duration: float
    resolution: str
    fps: float
    frame_count: int
    file_size: int
    imported_at: datetime
    has_labels: bool
    categories: list = None  # 新增

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
```

**1.2 _entry_to_mediainfo 读取新字段** [L592-604](file:///e:/project/Dusc%20AI%20CV%20GPU/modules/dataset_manager.py#L592-L604)

```python
def _entry_to_mediainfo(self, name, entry):
    return MediaInfo(
        # ... 现有字段 ...
        has_labels=entry.get("has_labels", False),
        categories=entry.get("categories", []),  # 新增
    )
```

**1.3 新增分类管理 API**

在 DatasetManager 类中新增以下方法：

```python
def list_categories(self):
    """返回所有分类名列表"""
    return list(self._registry.get("categories", []))

def add_category(self, name):
    """新建分类，重名则忽略"""
    cats = self._registry.setdefault("categories", [])
    if name not in cats:
        cats.append(name)
        self._save_registry()

def rename_category(self, old_name, new_name):
    """重命名分类，同步更新所有素材的 categories 字段"""
    cats = self._registry.get("categories", [])
    if old_name not in cats:
        return
    idx = cats.index(old_name)
    cats[idx] = new_name
    # 同步更新所有 media 条目
    for entry in self._registry.get("media", {}).values():
        if old_name in entry.get("categories", []):
            entry["categories"] = [new_name if c == old_name else c
                                   for c in entry["categories"]]
    self._save_registry()

def delete_category(self, name):
    """删除分类，同步从所有素材移除"""
    cats = self._registry.get("categories", [])
    if name in cats:
        cats.remove(name)
    for entry in self._registry.get("media", {}).values():
        if name in entry.get("categories", []):
            entry["categories"].remove(name)
    self._save_registry()

def set_media_categories(self, media_name, categories):
    """设置单个素材的分类列表（覆盖式）"""
    entry = self._registry.get("media", {}).get(media_name)
    if entry is None:
        return
    entry["categories"] = list(categories)
    self._save_registry()

def list_media_by_category(self, category):
    """返回属于指定分类的所有 MediaInfo"""
    return [m for m in self.list_media() if category in m.categories]
```

**1.4 兼容旧数据**

`_load_registry` 无需改动（`entry.get("categories", [])` 已处理缺失字段）。新导入的素材在 `import_video`/`import_images`/`scan_media_dir`/`extract_frames` 的 entry dict 中**无需显式初始化** categories（缺失时 `.get` 返回 `[]`），保持最小改动。

### 步骤 2：创建素材打包对话框（新文件 app/ui/pack_dialog.py）

```python
class PackDialog(QDialog):
    """素材打包对话框：双栏管理已标注图片素材的分类归属"""

    def __init__(self, project_root, dataset_manager, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.dataset_manager = dataset_manager
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("素材打包")
        self.setMinimumSize(1000, 640)

        layout = QVBoxLayout(self)

        # 顶部说明
        hint = QLabel("将已标注的图片素材归入分类，便于后续训练按分类选择。同一素材可属于多个分类。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 双栏 splitter
        splitter = QSplitter(Qt.Horizontal)

        # 左栏：已标注图片素材列表（支持多选）
        left_group = QGroupBox("已标注图片素材")
        left_layout = QVBoxLayout(left_group)
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.image_list.currentItemChanged.connect(self._on_image_selected)
        left_layout.addWidget(self.image_list)
        # 显示当前选中素材的分类归属
        self.current_cats_label = QLabel("未选择素材")
        left_layout.addWidget(self.current_cats_label)
        splitter.addWidget(left_group)

        # 右栏：分类管理
        right_group = QGroupBox("分类管理")
        right_layout = QVBoxLayout(right_group)

        # 分类操作按钮
        cat_btn_row = QHBoxLayout()
        self.btn_new_cat = QPushButton("新建分类")
        self.btn_new_cat.clicked.connect(self._on_new_category)
        self.btn_rename_cat = QPushButton("重命名")
        self.btn_rename_cat.clicked.connect(self._on_rename_category)
        self.btn_del_cat = QPushButton("删除分类")
        self.btn_del_cat.clicked.connect(self._on_delete_category)
        cat_btn_row.addWidget(self.btn_new_cat)
        cat_btn_row.addWidget(self.btn_rename_cat)
        cat_btn_row.addWidget(self.btn_del_cat)
        right_layout.addLayout(cat_btn_row)

        # 分类列表（带勾选框）
        self.cat_list = QListWidget()
        self.cat_list.itemChanged.connect(self._on_cat_check_changed)
        right_layout.addWidget(self.cat_list, 1)

        # 统计信息
        self.stats_label = QLabel("")
        right_layout.addWidget(self.stats_label)

        splitter.addWidget(right_group)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter, 1)

        # 底部关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignRight)

    def _load_data(self):
        """加载已标注图片素材和分类列表"""
        # 1. 加载已标注图片
        all_media = self.dataset_manager.list_media()
        labeled_images = [m for m in all_media
                          if m.media_type == "image"
                          and self.dataset_manager.has_label_for(m.name)]
        self._image_map = {}  # name -> MediaInfo
        self.image_list.clear()
        for i, m in enumerate(labeled_images, 1):
            item = QListWidgetItem(f"{i:03d}. {m.name}")
            item.setData(Qt.UserRole, m.name)
            self.image_list.addItem(item)
            self._image_map[m.name] = m

        # 2. 加载分类列表（带勾选状态）
        self._refresh_cat_list()
        self._update_stats()

    def _refresh_cat_list(self, checked_names=None):
        """刷新分类列表，保留勾选状态"""
        if checked_names is None:
            checked_names = set()
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for cat in self.dataset_manager.list_categories():
            item = QListWidgetItem(cat)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if cat in checked_names else Qt.Unchecked)
            self.cat_list.addItem(item)
        self.cat_list.blockSignals(False)

    def _on_image_selected(self, current, previous):
        """选中素材时，刷新分类勾选状态以反映该素材的归属"""
        if current is None:
            self.current_cats_label.setText("未选择素材")
            self._refresh_cat_list(set())
            return
        name = current.data(Qt.UserRole)
        m = self._image_map.get(name)
        if not m:
            return
        cats = m.categories or []
        self.current_cats_label.setText(
            f"当前: {name}\n分类: {', '.join(cats) if cats else '无'}"
        )
        self._refresh_cat_list(set(cats))

    def _on_cat_check_changed(self, item):
        """勾选/取消勾选分类时，立即保存到当前选中的素材"""
        current = self.image_list.currentItem()
        if current is None:
            return
        name = current.data(Qt.UserRole)
        # 收集当前所有勾选的分类
        checked = []
        for i in range(self.cat_list.count()):
            it = self.cat_list.item(i)
            if it.checkState() == Qt.Checked:
                checked.append(it.text())
        self.dataset_manager.set_media_categories(name, checked)
        # 更新本地缓存
        self._image_map[name].categories = checked
        self.current_cats_label.setText(
            f"当前: {name}\n分类: {', '.join(checked) if checked else '无'}"
        )
        self._update_stats()

    def _on_new_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
        if ok and name.strip():
            name = name.strip()
            self.dataset_manager.add_category(name)
            # 保留当前选中素材的勾选状态
            current = self.image_list.currentItem()
            checked = set()
            if current:
                m = self._image_map.get(current.data(Qt.UserRole))
                if m:
                    checked = set(m.categories or [])
            self._refresh_cat_list(checked)

    def _on_rename_category(self):
        current = self.cat_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择要重命名的分类")
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新名称:",
                                            text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            self.dataset_manager.rename_category(old_name, new_name.strip())
            self._load_data()  # 全量刷新

    def _on_delete_category(self):
        current = self.cat_list.currentItem()
        if not current:
            QMessageBox.information(self, "提示", "请先选择要删除的分类")
            return
        name = current.text()
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定删除分类 '{name}' 吗？\n素材本身不会被删除，仅移除分类归属。")
        if reply == QMessageBox.Yes:
            self.dataset_manager.delete_category(name)
            self._load_data()

    def _update_stats(self):
        cats = self.dataset_manager.list_categories()
        total = self.image_list.count()
        lines = [f"已标注图片: {total} 张 | 分类数: {len(cats)}"]
        for cat in cats:
            count = len(self.dataset_manager.list_media_by_category(cat))
            lines.append(f"  · {cat}: {count} 张")
        self.stats_label.setText("\n".join(lines))
```

### 步骤 3：在数据管理页接入按钮（app/ui/data_page.py）

**3.1 新增"素材打包"按钮** [L61-63 后](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L61-L63)

在"添加标签"按钮后、`addStretch()` 前插入：

```python
self.btn_pack = QPushButton("素材打包")
self.btn_pack.clicked.connect(self._on_pack)
btn_row.addWidget(self.btn_pack)
```

**3.2 新增导入** [文件顶部](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py)

```python
from app.ui.pack_dialog import PackDialog
```

**3.3 新增槽函数**（参照 `_on_annotate` 的模式，放在其附近）

```python
def _on_pack(self):
    """打开素材打包对话框"""
    dialog = PackDialog(self.project_root, self.dataset_manager, self)
    dialog.showMaximized()
    dialog.exec_()
    self._refresh_media()  # 刷新以反映分类归属变化
```

**3.4 媒体信息区显示分类归属** [L298-317 _show_info](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L298-L317)

在 `_show_info` 方法中，"已标注"行之后追加分类显示：

```python
# 现有代码: lines.append(f"已标注: {'是' if has_label else '否'}")
# 新增:
cats = getattr(m, 'categories', None) or []
lines.append(f"分类: {', '.join(cats) if cats else '无'}")
```

### 步骤 4：验证

1. **启动软件** → 数据管理页顶部应出现"素材打包"按钮。
2. **点击"素材打包"** → 弹出对话框，左栏列出所有已标注图片，右栏分类列表为空。
3. **新建分类** → 输入"微调用"，分类列表出现该项。
4. **选中左栏一张图片** → 勾选"微调用" → 关闭对话框 → 媒体信息区应显示"分类: 微调用"。
5. **再次打开对话框** → 选中该图片 → 勾选状态应保留（持久化生效）。
6. **选中多张图片** → 应能批量勾选分类（通过 _on_cat_check_changed 处理当前选中项；多选批量操作可作为后续优化）。
7. **重命名分类** → 原"微调用"改为"训练用" → 所有引用该分类的素材应同步更新。
8. **删除分类** → 素材本身不删除，仅移除分类归属。
9. **检查 media_registry.json** → media 条目应有 `categories` 字段，顶层应有 `categories` section。

## 假设与决策

- **只对已标注图片开放归类**：未标注图片无法参与训练，不列入打包范围。`_load_data` 用 `has_label_for` 过滤。
- **分类归属即时保存**：每次勾选/取消勾选立即写 registry，避免用户忘记保存。
- **不复制文件**：分类是元数据，不产生文件冗余。后续训练时按 `categories` 字段筛选素材即可。
- **不修改现有 import 方法**：新导入的素材 categories 默认为 `[]`，通过 `.get("categories", [])` 兼容。
- **遗留的 app/models/media_info.py 不动**：DataPage 实际使用的是 `modules/dataset_manager.py` 的 MediaInfo，遗留版本不影响新功能。

## 影响范围

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `modules/dataset_manager.py` | 修改 | MediaInfo 加字段 + 新增 6 个分类 API |
| `app/ui/pack_dialog.py` | 新建 | PackDialog 对话框 |
| `app/ui/data_page.py` | 修改 | 新增按钮 + 槽函数 + 信息区显示分类 |
| `configs/media_registry.json` | 自动扩展 | 运行时新增 categories 字段和 section |

不改动：label_editor_dialog.py、train_page.py、main.py、resource 目录结构。
