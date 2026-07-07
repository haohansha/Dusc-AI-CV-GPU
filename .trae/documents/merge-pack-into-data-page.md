# 素材打包合并到数据管理页

## 概述

将独立弹出的"素材打包"对话框合并进数据管理页本体：左栏图片素材拆分为"已标注图片"和"未标注图片"两个列表；右栏底部新增"分类管理"GroupBox；顶部按钮栏去掉"素材打包"按钮。

## 当前状态分析

### 当前布局结构（`app/ui/data_page.py`）

```
┌─ 顶部按钮栏（QHBoxLayout）──────────────────────────────────┐
│ 导入视频 │ 导入图片 │ 导入标签 │ 扫描 │ 批量删除 │ 抽帧 │ 添加标签 │ 素材打包 │
├─ QSplitter（水平三栏）──────────────────────────────────┤
│ 左栏(250)        │ 中栏(600)        │ 右栏(200)         │
│ ┌素材列表┐       │ ┌预览区┐         │ ┌媒体信息┐        │
│ │视频素材│       │ │       │        │ │ 文件名  │        │
│ │ video │       │ │  QPixmap│       │ │ 类型    │        │
│ │图片素材│       │ │       │        │ │ 路径    │        │
│ │ image │       │ │       │        │ │ 已标注  │        │
│ │标签管理│       │ └───────┘        │ │ 分类    │        │
│ │ label │       │                  │ │ 导入时间│        │
│ └───────┘       │                  │ └─────────┘        │
│                 │                  │ [addStretch 空白]  │
└─────────────────┴──────────────────┴─────────────────────┘
```

### 关键代码位置

| 关注点 | 文件:行号 |
|---|---|
| 顶部按钮栏（含"素材打包"按钮） | data_page.py:37-71 |
| "素材打包"按钮定义 | data_page.py:66-68 |
| `_on_pack` 槽函数 | data_page.py:640-645 |
| PackDialog 导入 | data_page.py:12 |
| 三栏 QSplitter | data_page.py:74 |
| 左栏 `image_list` 创建 | data_page.py:90-96 |
| 中栏预览区 | data_page.py:110-120 |
| 右栏 `info_label` + stretch | data_page.py:122-133 |
| Splitter sizes/stretch | data_page.py:135-138 |
| `_refresh_media` 图片列表填充 | data_page.py:153-201 |
| `_on_image_selected`（图片选中槽） | data_page.py:224-241 |
| `_show_info` 分类归属行 | data_page.py:322-323 |
| PackDialog 分类管理逻辑 | pack_dialog.py:24-219 |
| DatasetManager 分类 API | dataset_manager.py:612-658 |

## 改造后布局简图

```
┌─ 顶部按钮栏 ─────────────────────────────────────────────────┐
│ 导入视频 │ 导入图片 │ 导入标签 │ 扫描 │ 批量删除 │ 抽帧 │ 添加标签 │
│                              （素材打包按钮已移除）            │
├─ QSplitter（水平三栏）──────────────────────────────────────┤
│ 左栏(280)          │ 中栏(560)      │ 右栏(280)             │
│ ┌素材列表──────┐   │ ┌预览区────┐   │ ┌媒体信息────────┐   │
│ │ 视频素材     │   │ │           │   │ │ 文件名: xxx.jpg│   │
│ │ ┌video_list┐│   │ │           │   │ │ 类型: 图片     │   │
│ │ └──────────┘│   │ │  QPixmap  │   │ │ 路径: ...      │   │
│ │             │   │ │           │   │ │ 大小: 0.5 MB   │   │
│ │ 已标注图片 ✓│   │ │           │   │ │ 已标注: 是     │   │
│ │ ┌img_labeled│ │   │ │           │   │ │ 分类: 微调用   │   │
│ │ └──────────┘│   │ │           │   │ │ 导入时间: ...  │   │
│ │             │   │ └───────────┘   │ └────────────────┘   │
│ │ 未标注图片   │   │                 │ ┌分类管理────────┐   │
│ │ ┌img_unlabeled│ │                 │ │[新建][重命名][删除]│
│ │ └──────────┘│   │                 │ │ ☑ 微调用   (5) │   │
│ │             │   │                 │ │ ☐ 测试用   (3) │   │
│ │ 标签管理     │   │                 │ │ ☐ 验证集   (0) │   │
│ │ ┌label_list┐│   │                 │ │                │   │
│ │ └──────────┘│   │                 │ │ 已标注:8 分类:3│   │
│ └─────────────┘   │                 │ └────────────────┘   │
└───────────────────┴─────────────────┴──────────────────────┘
```

**关键变化**：
1. 左栏图片素材拆分为两个 QListWidget（已标注/未标注），原 image_list 移除
2. 右栏底部新增"分类管理"GroupBox（含操作按钮 + 带勾选框的分类列表 + 统计信息）
3. 顶部按钮栏移除"素材打包"按钮
4. 选中已标注图片时，右栏分类勾选自动同步该素材的分类归属
5. 勾选/取消勾选分类时，立即保存到 registry

## 实施步骤

### 步骤 1：去掉素材打包按钮 + PackDialog 导入（data_page.py）

**1.1 移除按钮定义** [L66-68](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L66-L68)

删除：
```python
self.btn_pack = QPushButton("素材打包")
self.btn_pack.clicked.connect(self._on_pack)
btn_row.addWidget(self.btn_pack)
```

**1.2 移除导入** [L12](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L12)

删除：`from app.ui.pack_dialog import PackDialog`

**1.3 移除槽函数** [L640-645](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L640-L645)

删除整个 `_on_pack` 方法。

### 步骤 2：左栏图片素材拆分为两个列表（data_page.py）

**2.1 替换原 image_list 创建代码** [L90-96](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L90-L96)

将原来的"图片素材"列表替换为两个独立列表：

```python
# 已标注图片
labeled_label = QLabel("已标注图片")
left_layout.addWidget(labeled_label)
self.image_labeled_list = QListWidget()
self.image_labeled_list.setSelectionMode(QListWidget.SingleSelection)
self.image_labeled_list.setContextMenuPolicy(Qt.CustomContextMenu)
self.image_labeled_list.currentRowChanged.connect(self._on_image_selected)
self.image_labeled_list.customContextMenuRequested.connect(self._on_image_context_menu)
left_layout.addWidget(self.image_labeled_list, 1)

# 未标注图片
unlabeled_label = QLabel("未标注图片")
left_layout.addWidget(unlabeled_label)
self.image_unlabeled_list = QListWidget()
self.image_unlabeled_list.setSelectionMode(QListWidget.SingleSelection)
self.image_unlabeled_list.setContextMenuPolicy(Qt.CustomContextMenu)
self.image_unlabeled_list.currentRowChanged.connect(self._on_image_selected)
self.image_unlabeled_list.customContextMenuRequested.connect(self._on_image_context_menu)
left_layout.addWidget(self.image_unlabeled_list, 1)
```

**2.2 修改 `_refresh_media`** [L153-201](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L153-L201)

将原 image_list 填充逻辑替换为按 `has_label_for` 拆分到两个列表：

```python
# 已标注图片
self.image_labeled_list.clear()
labeled_idx = 1
for m in media:
    if m.media_type != "image":
        continue
    if not self.dataset_manager.has_label_for(m.name):
        continue
    cats_str = f"  [{', '.join(m.categories)}]" if m.categories else ""
    item = QListWidgetItem(f"{labeled_idx:03d}. {m.name}{cats_str}")
    item.setData(Qt.UserRole, m)
    item.setData(Qt.UserRole + 1, idx)  # 保留统一编号供批量删除
    self.image_labeled_list.addItem(item)
    labeled_idx += 1
    idx += 1

# 未标注图片
self.image_unlabeled_list.clear()
unlabeled_idx = 1
for m in media:
    if m.media_type != "image":
        continue
    if self.dataset_manager.has_label_for(m.name):
        continue
    item = QListWidgetItem(f"{unlabeled_idx:03d}. {m.name}")
    item.setData(Qt.UserRole, m)
    item.setData(Qt.UserRole + 1, idx)
    self.image_unlabeled_list.addItem(item)
    unlabeled_idx += 1
    idx += 1
```

**2.3 修改 `_on_image_selected`** [L224-241](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L224-L241)

让两个 image_list 共享同一槽函数。需判断信号来源：

```python
def _on_image_selected(self, row):
    if row < 0:
        return
    # 判断来自哪个 list
    list_widget = self.sender()
    if list_widget is self.image_labeled_list:
        item = self.image_labeled_list.item(row)
    elif list_widget is self.image_unlabeled_list:
        item = self.image_unlabeled_list.item(row)
    else:
        return  # 来自 video_list 等其他列表
    if not item:
        return
    m = item.data(Qt.UserRole)
    self._current_media = m
    self._show_preview(m)
    self._show_info(m)
    # 选中已标注图片时刷新分类勾选
    if list_widget is self.image_labeled_list:
        self._refresh_cat_checkstate(m)
    else:
        self._clear_cat_checkstate()
    # 清空其他 image_list 的选中（避免两个列表同时选中）
    if list_widget is self.image_labeled_list:
        self.image_unlabeled_list.setCurrentRow(-1)
    else:
        self.image_labeled_list.setCurrentRow(-1)
    # 状态栏更新
    self.status_label.setText(
        f"共 {total} 个素材 | 当前: {m.name}"
    )
```

**2.4 修改右键菜单 `_on_image_context_menu`**

参照 `_on_image_selected` 的 sender 判断方式，从对应的 list 取 currentItem。

### 步骤 3：右栏底部新增分类管理 GroupBox（data_page.py）

**3.1 在 `_setup_ui` 右栏布局中插入分类管理** [L122-133](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L122-L133)

```python
# 右栏：媒体信息
right_group = QGroupBox("媒体信息")
right_layout = QVBoxLayout(right_group)
self.info_label = QLabel("未选择素材")
self.info_label.setWordWrap(True)
self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
self.info_label.setStyleSheet("QLabel { background: #f5f5f5; padding: 6px; }")
right_layout.addWidget(self.info_label)

# 新增：分类管理 GroupBox
cat_group = QGroupBox("分类管理")
cat_layout = QVBoxLayout(cat_group)

# 分类操作按钮行
cat_btn_row = QHBoxLayout()
self.btn_new_cat = QPushButton("新建")
self.btn_new_cat.clicked.connect(self._on_new_category)
self.btn_rename_cat = QPushButton("重命名")
self.btn_rename_cat.clicked.connect(self._on_rename_category)
self.btn_del_cat = QPushButton("删除")
self.btn_del_cat.clicked.connect(self._on_delete_category)
cat_btn_row.addWidget(self.btn_new_cat)
cat_btn_row.addWidget(self.btn_rename_cat)
cat_btn_row.addWidget(self.btn_del_cat)
cat_layout.addLayout(cat_btn_row)

# 带勾选框的分类列表
self.cat_list = QListWidget()
self.cat_list.itemChanged.connect(self._on_cat_check_changed)
cat_layout.addWidget(self.cat_list, 1)

# 统计信息
self.cat_stats_label = QLabel("")
self.cat_stats_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
cat_layout.addWidget(self.cat_stats_label)

right_layout.addWidget(cat_group)
```

### 步骤 4：移植 PackDialog 的分类管理方法到 DataPage（data_page.py）

从 `pack_dialog.py` 移植以下方法到 DataPage 类，并适配 DataPage 的上下文：

**4.1 `_refresh_cat_list`**（刷新分类列表，带勾选状态）

```python
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
    self._update_cat_stats()

def _refresh_cat_checkstate(self, m):
    """选中已标注图片时，刷新分类勾选状态"""
    cats = m.categories or []
    self._refresh_cat_list(set(cats))

def _clear_cat_checkstate(self):
    """未标注图片时，清空所有勾选"""
    self._refresh_cat_list(set())
```

**4.2 `_on_cat_check_changed`**（勾选变化时保存到 registry）

```python
def _on_cat_check_changed(self, item):
    """勾选/取消勾选分类时，立即保存到当前选中的已标注图片"""
    if not self._current_media or self._current_media.media_type != "image":
        return
    if not self.dataset_manager.has_label_for(self._current_media.name):
        return  # 未标注图片不参与分类
    name = self._current_media.name
    # 收集当前所有勾选的分类
    checked = []
    for i in range(self.cat_list.count()):
        it = self.cat_list.item(i)
        if it.checkState() == Qt.Checked:
            checked.append(it.text())
    self.dataset_manager.set_media_categories(name, checked)
    # 更新 MediaInfo 本地缓存
    self._current_media.categories = checked
    # 更新已标注图片列表项显示
    self._refresh_image_labeled_item_text(name, checked)
    # 更新媒体信息区
    self._show_info(self._current_media)
    self._update_cat_stats()
```

**4.3 `_update_cat_stats`**（统计信息）

```python
def _update_cat_stats(self):
    cats = self.dataset_manager.list_categories()
    labeled_count = self.image_labeled_list.count()
    lines = [f"已标注图片: {labeled_count} 张 | 分类数: {len(cats)}"]
    for cat in cats:
        count = len(self.dataset_manager.list_media_by_category(cat))
        lines.append(f"  · {cat}: {count} 张")
    self.cat_stats_label.setText("\n".join(lines))
```

**4.4 分类操作方法**（直接移植自 PackDialog）

```python
def _on_new_category(self):
    name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
    if ok and name.strip():
        name = name.strip()
        self.dataset_manager.add_category(name)
        # 保留当前选中素材的勾选状态
        checked = set()
        if self._current_media and self._current_media.media_type == "image":
            checked = set(self._current_media.categories or [])
        self._refresh_cat_list(checked)

def _on_rename_category(self):
    current = self.cat_list.currentItem()
    if not current:
        QMessageBox.information(self, "提示", "请先选择要重命名的分类")
        return
    old_name = current.text()
    new_name, ok = QInputDialog.getText(self, "重命名分类", "新名称:", text=old_name)
    if ok and new_name.strip() and new_name.strip() != old_name:
        self.dataset_manager.rename_category(old_name, new_name.strip())
        self._refresh_media()
        # 重新选中当前素材以恢复勾选状态
        if self._current_media:
            self._refresh_cat_checkstate(self._current_media)

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
        self._refresh_media()
        if self._current_media:
            self._refresh_cat_checkstate(self._current_media)
```

**4.5 刷新已标注列表项文本的辅助方法**

```python
def _refresh_image_labeled_item_text(self, name, categories):
    """更新已标注图片列表中指定项的文本（追加分类后缀）"""
    for i in range(self.image_labeled_list.count()):
        item = self.image_labeled_list.item(i)
        m = item.data(Qt.UserRole)
        if m.name == name:
            cats_str = f"  [{', '.join(categories)}]" if categories else ""
            item.setText(f"{i+1:03d}. {name}{cats_str}")
            break
```

### 步骤 5：初始化时加载分类列表

**5.1 在 DataPage 构造函数或初始化方法中调用**

```python
# 初始化分类列表（空勾选状态）
self._refresh_cat_list()
```

### 步骤 6：删除 PackDialog 文件

确认功能全部移植后，删除 `app/ui/pack_dialog.py`（保留计划文件 `.trae/documents/media-pack-feature.md` 作为历史记录）。

## 假设与决策

- **图片列表拆分**：采用用户选择的"拆为两个独立 QListWidget"方案，左栏从 3 个 list 变为 4 个 list（视频/已标注图片/未标注图片/标签管理）。
- **分类管理只对已标注图片生效**：选中未标注图片时，右栏分类勾选清空且不响应勾选操作（避免给无标签图片打分类）。
- **两个图片列表互斥选中**：选中一个列表的项时，另一个列表自动 `setCurrentRow(-1)`，避免预览/信息显示混乱。
- **右栏宽度调整**：原 splitter sizes `[250, 600, 200]` 改为 `[280, 560, 280]`，给右栏分类管理更多空间。
- **右键菜单兼容**：两个图片列表共用 `_on_image_context_menu`，通过 `self.sender()` 判断来源。
- **批量删除兼容**：`_on_delete` 中的图片遍历需同时检查两个列表的选中项（或保持统一编号机制）。

## 验证步骤

1. 启动软件 → 数据管理页顶部按钮栏无"素材打包"按钮。
2. 左栏应显示 4 个分组：视频素材 / 已标注图片 / 未标注图片 / 标签管理。
3. 已标注图片列表项后缀显示 `[分类名]`，未标注图片无后缀。
4. 选中已标注图片 → 右栏分类勾选自动同步该图片的分类归属。
5. 勾选/取消勾选分类 → 立即保存，列表项后缀和媒体信息区实时更新。
6. 选中未标注图片 → 右栏分类勾选清空，无法操作勾选。
7. 两个图片列表互斥：选一个时另一个自动取消选中。
8. 新建/重命名/删除分类正常工作，统计信息实时更新。
9. 右键菜单在两个图片列表上均能正常弹出（删除/查看等操作）。
10. 批量删除功能能正确处理两个图片列表的选中项。

## 影响范围

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `app/ui/data_page.py` | 修改 | 删除素材打包按钮 + 图片列表拆分 + 右栏新增分类管理 + 移植分类管理方法 |
| `app/ui/pack_dialog.py` | 删除 | 功能已合并到 DataPage |

不改动：dataset_manager.py（分类 API 已就绪）、label_editor_dialog.py、main.py、configs/media_registry.json。
