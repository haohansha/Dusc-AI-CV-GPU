# 数据管理页分类管理优化

## 概述

三项优化：① 限制只有选中已标注图片时，右栏分类管理的分类项才能勾选；② 分类管理按钮区新增"批量选中"功能，支持批量给多张已标注图片打分类；③ 调整布局尺寸，让左栏素材列表和中栏预览区增长约 30%。

## 当前状态分析

### 关键代码位置

| 关注点 | 文件:行号 |
|---|---|
| 主窗口最小尺寸 `setMinimumSize(1200, 800)` | app/main_window.py:33 |
| 主窗口启动 `showMaximized()` | app/main.py:39 |
| Splitter sizes `[280, 560, 280]` + stretch 1:3:1 | data_page.py:162-165 |
| 预览区 `setMinimumSize(480, 360)` + `SizePolicy.Ignored` | data_page.py:118-119 |
| 左栏 4 个 QListWidget（均 SingleSelection，stretch=1） | data_page.py:77-109 |
| 分类管理 GroupBox（按钮 + cat_list + 统计） | data_page.py:137-158 |
| `_refresh_cat_list`（设置 ItemIsUserCheckable） | data_page.py:709-721 |
| `_on_cat_check_changed`（软阻止未标注图片勾选） | data_page.py:732-752 |
| `_refresh_cat_checkstate` / `_clear_cat_checkstate` | data_page.py:723-730 |
| `_on_image_selected`（通过 sender 判断来源列表） | data_page.py:270-303 |
| 互斥逻辑（setCurrentRow(-1)） | data_page.py:252-254, 288-295, 309-311 |
| 现有批量删除（自定义对话框 + 编号范围） | data_page.py:552-674 |
| `has_label_for` 调用位置 | data_page.py:204, 384, 736 |
| DatasetManager 分类 API | dataset_manager.py:612-658 |

### 当前问题

1. **分类勾选软阻止**：`_on_cat_check_changed` 仅 `return` 不保存，但 UI 上用户仍可勾选，刷新后会被重置，体验混乱。
2. **无批量操作**：分类管理只能单张图片逐个勾选，效率低。
3. **布局偏小**：预览区最小 480×360，splitter 初始 280:560:280，在 1080p 屏幕上列表和预览区偏短。

## 设计决策

1. **硬阻止方案**：未选中已标注图片时，`cat_list` 整体 `setEnabled(False)`，分类项不可勾选；选中已标注图片时 `setEnabled(True)`。
2. **批量选中方案**：新增"批量选中"按钮 → 弹出分类选择对话框（多选）→ 将已标注图片列表中**当前选中的多张图片**批量归入这些分类。要求已标注图片列表改为 `ExtendedSelection` 多选模式。
3. **多选与单选协调**：已标注图片列表改为 `ExtendedSelection`（Ctrl/Shift 多选），未标注图片列表保持 `SingleSelection`。选中多张时，分类勾选反映**最后选中（currentItem）**的那张；批量选中按钮处理所有选中项。
4. **尺寸调整方案**：综合调整——主窗口最小尺寸增大 + splitter sizes 调整 + 预览区最小尺寸增大，整体高度拉伸 30%。

## 实施步骤

### 步骤 1：硬阻止未标注图片时分类勾选（data_page.py）

**1.1 修改 `_refresh_cat_list` 加 enabled 参数** [L709-721](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L709-L721)

```python
def _refresh_cat_list(self, checked_names=None, enabled=True):
    """刷新分类列表，保留勾选状态，并可控制列表是否可用"""
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
    self.cat_list.setEnabled(enabled)
    self._update_cat_stats()
```

**1.2 修改 `_refresh_cat_checkstate` 和 `_clear_cat_checkstate`** [L723-730](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L723-L730)

```python
def _refresh_cat_checkstate(self, m):
    """选中已标注图片时，刷新分类勾选状态，启用列表"""
    cats = m.categories or []
    self._refresh_cat_list(set(cats), enabled=True)

def _clear_cat_checkstate(self):
    """未标注图片/视频/标签时，清空勾选，禁用列表"""
    self._refresh_cat_list(set(), enabled=False)
```

**1.3 初始化时禁用分类列表**

DataPage 初始化（`_setup_ui` 末尾或 `_refresh_media` 初次调用时）默认 `cat_list.setEnabled(False)`，因为启动时无选中素材。

### 步骤 2：已标注图片列表改为多选模式（data_page.py）

**2.1 修改选择模式** [L87](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L87)

```python
# 原：self.image_labeled_list.setSelectionMode(QAbstractItemView.SingleSelection)
self.image_labeled_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
```

未标注图片列表保持 `SingleSelection`（L96 不变）。

**2.2 信号连接保持不变**

`currentRowChanged` 仍会触发，`_on_image_selected` 通过 `currentItem()` 取最后选中项，用于预览和信息显示。

### 步骤 3：新增"批量选中"按钮和功能（data_page.py）

**3.1 在分类管理按钮行新增按钮** [L140-150](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L140-L150)

```python
cat_btn_row = QHBoxLayout()
self.btn_new_cat = QPushButton("新建")
self.btn_new_cat.clicked.connect(self._on_new_category)
self.btn_rename_cat = QPushButton("重命名")
self.btn_rename_cat.clicked.connect(self._on_rename_category)
self.btn_del_cat = QPushButton("删除")
self.btn_del_cat.clicked.connect(self._on_delete_category)
self.btn_batch_cat = QPushButton("批量选中")
self.btn_batch_cat.setToolTip("将当前选中的多张已标注图片批量归入指定分类")
self.btn_batch_cat.clicked.connect(self._on_batch_assign)
cat_btn_row.addWidget(self.btn_new_cat)
cat_btn_row.addWidget(self.btn_rename_cat)
cat_btn_row.addWidget(self.btn_del_cat)
cat_btn_row.addWidget(self.btn_batch_cat)
```

**3.2 新增 `_on_batch_assign` 方法**

```python
def _on_batch_assign(self):
    """批量给选中的多张已标注图片归入指定分类"""
    # 收集已标注图片列表中所有选中项
    selected_items = self.image_labeled_list.selectedItems()
    if not selected_items:
        QMessageBox.information(self, "提示", "请先在已标注图片列表中选择要批量归类的图片\n（按住 Ctrl 或 Shift 可多选）")
        return
    # 收集所有分类供选择
    cats = self.dataset_manager.list_categories()
    if not cats:
        QMessageBox.information(self, "提示", "暂无分类，请先点击'新建'创建分类")
        return
    # 弹出多选对话框
    from PyQt5.QtWidgets import QDialog as _QDialog, QVBoxLayout as _QVBoxLayout, \
        QListWidget as _QListWidget, QListWidgetItem as _QListWidgetItem, \
        QDialogButtonBox as _QDialogButtonBox, QLabel as _QLabel
    dlg = _QDialog(self)
    dlg.setWindowTitle("批量归类")
    dlg.setMinimumWidth(320)
    dl = _QVBoxLayout(dlg)
    dl.addWidget(_QLabel(f"将 {len(selected_items)} 张图片批量归入以下分类（可多选）："))
    sel = _QListWidget()
    sel.setSelectionMode(_QListWidget.MultiSelection)
    for c in cats:
        it = _QListWidgetItem(c)
        sel.addItem(it)
    dl.addWidget(sel)
    btns = _QDialogButtonBox(_QDialogButtonBox.Ok | _QDialogButtonBox.Cancel)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    dl.addWidget(btns)
    if dlg.exec_() != _QDialog.Accepted:
        return
    target_cats = [sel.item(i).text() for i in range(sel.count()) if sel.item(i).isSelected()]
    if not target_cats:
        QMessageBox.information(self, "提示", "未选择任何分类")
        return
    # 批量设置每张图片的分类（合并已有分类 + 新分类）
    changed = 0
    for item in selected_items:
        m = item.data(Qt.UserRole)
        # 合并：保留原有不在 target 中的分类 + 新增 target_cats（去重）
        existing = set(m.categories or [])
        merged = existing | set(target_cats)
        self.dataset_manager.set_media_categories(m.name, list(merged))
        m.categories = list(merged)
        changed += 1
    # 刷新 UI
    self._refresh_media()
    self._update_cat_stats()
    QMessageBox.information(self, "完成", f"已将 {changed} 张图片批量归入分类：{', '.join(target_cats)}")
```

### 步骤 4：调整布局尺寸（data_page.py + main_window.py）

**4.1 主窗口最小尺寸增大 30%** [main_window.py:33](file:///e:/project/Dusc%20AI%20CV%20GPU/app/main_window.py#L33)

```python
# 原：self.setMinimumSize(1200, 800)
self.setMinimumSize(1200, 1040)  # 高度从 800 → 1040（+30%）
```

**4.2 预览区最小尺寸增大 30%** [data_page.py:118](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L118)

```python
# 原：self.preview_label.setMinimumSize(480, 360)
self.preview_label.setMinimumSize(480, 468)  # 高度 360 → 468（+30%）
```

**4.3 Splitter sizes 调整** [data_page.py:165](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L165)

```python
# 原：splitter.setSizes([280, 560, 280])
splitter.setSizes([300, 700, 300])  # 中栏从 560 → 700（+25%），左右栏略增
```

**4.4 Splitter stretchFactor 调整** [data_page.py:162-164](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L162-L164)

```python
# 保持 1:3:1 不变，让中栏继续主导拉伸
splitter.setStretchFactor(0, 1)
splitter.setStretchFactor(1, 3)
splitter.setStretchFactor(2, 1)
```

## 假设与决策

- **硬阻止**：通过 `cat_list.setEnabled(False)` 整体禁用，视觉上灰色不可点击，比逐项禁用 flag 更简洁。
- **批量选中 = 批量归类**：把多张选中的已标注图片批量归入指定分类（合并原有分类，不覆盖）。
- **多选模式仅限已标注图片列表**：未标注图片列表保持单选（无标签的图片不参与分类，多选无意义）。
- **预览/信息显示当前选中项**：多选时仍以 `currentItem()`（最后选中项）作为预览和信息显示对象，分类勾选也反映该项。
- **尺寸增长 30%**：主要通过增大主窗口最小高度 + 预览区最小高度 + splitter 中栏初始尺寸实现。主窗口启动时 `showMaximized()`，所以实际显示高度由屏幕决定，最小高度调整保证窗口缩小时列表/预览区不会被过度压缩。

## 验证步骤

1. 启动软件 → 数据管理页 → 未选中任何素材时，右栏分类列表灰色不可勾选。
2. 选中已标注图片 → 分类列表启用，勾选状态反映该图片分类。
3. 选中未标注图片 → 分类列表禁用，无法勾选。
4. 选中视频 → 分类列表禁用。
5. 选中标签 → 分类列表禁用。
6. 在已标注图片列表中按住 Ctrl 多选 3 张 → 点击"批量选中" → 弹出对话框选择"微调用" → 确认 → 3 张图片均归入"微调用"，列表项后缀显示 `[微调用]`。
7. 批量选中时若未选任何图片 → 提示"请先选择"。
8. 批量选中时若无分类 → 提示"请先新建分类"。
9. 布局检查：窗口最大化时，左栏列表和中栏预览区比之前明显更高（约 30%），右栏分类管理不被挤压。
10. 窗口缩小到最小尺寸时，预览区仍保持 480×468，列表不被压缩到无法显示。

## 影响范围

| 文件 | 改动 |
|---|---|
| `app/ui/data_page.py` | 分类列表启用/禁用 + 已标注列表改多选 + 新增批量选中按钮和方法 + 布局尺寸调整 |
| `app/main_window.py` | 主窗口最小高度 800 → 1040 |

不改动：dataset_manager.py（分类 API 已就绪）、main.py、label_editor_dialog.py。
