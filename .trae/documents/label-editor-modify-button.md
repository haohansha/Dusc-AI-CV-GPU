# 标注编辑器：新增"修改"按钮 + 选中状态联动

## Summary

在手动输入区新增"修改"按钮，用于更新当前选中的标注框参数。按钮启用状态与右栏标注框选中状态联动：未选中时灰色禁用，选中时亮起可点。同时支持点击画布空白处取消选中。

## Current State Analysis

### 当前实现（基于 Phase 1 探索 [app/ui/label_editor_dialog.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py)）

- **手动输入区按钮**（[L400-L402](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L400-L402)）：只有"添加"按钮，无"修改"按钮。
- **`_on_box_selected(row)`**（[L627-L645](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L627-L645)）：选中右栏列表项时同步类别下拉框 + xc/yc/w/h 输入框，但**没有启用/禁用按钮的逻辑**。
- **`_refresh_box_list()`**（[L616-L625](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L616-L625)）：刷新列表时会 `box_list.clear()`，导致 `currentRowChanged` 触发为 -1，但当前未处理 -1 的清理逻辑。
- **`_on_class_changed()`**（[L557-L575](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L557-L575)：切换类别时若右栏有选中框，会自动修改该框的类别。
- **画布鼠标事件**（[L204-L227](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L204-L227)）：仅在快速模式下响应拖动画框，**没有点击选中已有框或点击空白取消选中的逻辑**。

### 关键发现

1. 当前选中状态完全靠 `box_list.currentRow()`，没有"取消选中"的显式入口。
2. `_on_class_changed` 已实现"切换类别自动改选中框类别"——这个行为可能与"修改"按钮冲突。需要决策：保留自动修改 vs 改为手动修改。

## Proposed Changes

### 改动文件

**`e:\project\Dusc AI CV GPU\app\ui\label_editor_dialog.py`**

---

#### 改动 1：手动输入区新增"修改"按钮

**位置**：[L400-L402](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L400-L402)

把"添加"按钮改成"添加 + 修改"两个按钮的水平布局：

```python
# 原来：
self.btn_add_manual = QPushButton("添加")
self.btn_add_manual.clicked.connect(self._on_add_manual)
manual_form.addRow(self.btn_add_manual)

# 改为：
btn_row_manual = QHBoxLayout()
self.btn_add_manual = QPushButton("添加")
self.btn_add_manual.clicked.connect(self._on_add_manual)
btn_row_manual.addWidget(self.btn_add_manual)

self.btn_modify = QPushButton("修改")
self.btn_modify.setToolTip("更新当前选中的标注框参数")
self.btn_modify.clicked.connect(self._on_modify_box)
self.btn_modify.setEnabled(False)  # 初始灰色禁用
btn_row_manual.addWidget(self.btn_modify)
manual_form.addRow(btn_row_manual)
```

---

#### 改动 2：新增 `_on_modify_box` 方法

**位置**：在 `_on_add_manual` 之后新增

```python
def _on_modify_box(self):
    """用当前输入区的值更新选中的标注框"""
    row = self.box_list.currentRow()
    if row < 0 or not self._current_image:
        return
    boxes = self._boxes_map.get(self._current_image.name, [])
    if row >= len(boxes):
        return
    new_cid = self.combo_class.currentIndex()
    new_xc = self.spin_xc.value()
    new_yc = self.spin_yc.value()
    new_w = self.spin_w.value()
    new_h = self.spin_h.value()
    if new_w <= 0 or new_h <= 0:
        QMessageBox.warning(self, "提示", "宽度和高度必须大于 0")
        return
    boxes[row] = (new_cid, new_xc, new_yc, new_w, new_h)
    self._dirty.add(self._current_image.name)
    self._refresh_box_list()
    # 重新选中（_refresh_box_list 会清空选中）
    self.box_list.setCurrentRow(row)
    self.status_bar.showMessage(f"已更新标注框 #{row + 1}")
```

---

#### 改动 3：`_on_box_selected` 联动按钮启用状态

**位置**：修改 [L627-L645](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L627-L645)

```python
def _on_box_selected(self, row):
    """选中右栏标注框时，同步类别下拉框、坐标输入框，并启用修改按钮"""
    self.canvas.set_selected(row)
    # 联动修改按钮：row >= 0 时启用，否则禁用
    self.btn_modify.setEnabled(row >= 0)
    if row < 0 or not self._current_image:
        return
    boxes = self._boxes_map.get(self._current_image.name, [])
    if row >= len(boxes):
        return
    cid, xc, yc, w, h = boxes[row]
    # 同步类别下拉框（临时阻塞信号，避免触发 _on_class_changed）
    if 0 <= cid < len(self._class_names):
        self.combo_class.blockSignals(True)
        self.combo_class.setCurrentIndex(cid)
        self.combo_class.blockSignals(False)
    # 同步坐标输入框
    self.spin_xc.setValue(xc)
    self.spin_yc.setValue(yc)
    self.spin_w.setValue(w)
    self.spin_h.setValue(h)
```

---

#### 改动 4：点击画布空白处取消选中

**位置**：修改 `AnnotationCanvas.mousePressEvent`（[L204-L212](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L204-L212)）

在快速模式下，如果点击位置不在任何已有标注框内，则通知 dialog 取消选中：

```python
def mousePressEvent(self, event):
    # 只有快速模式开启才响应
    if not self._quick_mode:
        return
    if event.button() != Qt.LeftButton:
        return
    # 如果没有图片，直接返回
    if not self._pixmap:
        return
    # 检查是否点击在某个已有标注框内（用于选中已有框）
    clicked_idx = self._hit_test(event.pos())
    if clicked_idx >= 0:
        # 点击在已有框内 → 通知 dialog 选中该框（不开始画框）
        if self._on_box_clicked_cb:
            self._on_box_clicked_cb(clicked_idx)
        return
    # 点击在空白处 → 通知 dialog 取消选中，开始画新框
    if self._on_clear_selection_cb:
        self._on_clear_selection_cb()
    self._drawing = True
    self._start_point = event.pos()
    self._end_point = event.pos()
```

---

#### 改动 5：AnnotationCanvas 新增 `_hit_test` 和回调

**位置**：在 `set_on_box_drawn` 之后新增

```python
def set_on_box_clicked(self, callback):
    """设置点击已有框的回调（由 dialog 设置）"""
    self._on_box_clicked_cb = callback

def set_on_clear_selection(self, callback):
    """设置点击空白处取消选中的回调（由 dialog 设置）"""
    self._on_clear_selection_cb = callback

def _hit_test(self, pos):
    """检测点击位置是否在某个已有标注框内，返回索引（-1 表示不在任何框内）"""
    if not self._pixmap:
        return -1
    offset = self._image_offset()
    img_w = self._pixmap.width()
    img_h = self._pixmap.height()
    for idx, (cid, xc, yc, w, h) in enumerate(self._boxes):
        # 归一化 → 画布像素
        cx = offset.x() + xc * img_w * self._scale
        cy = offset.y() + yc * img_h * self._scale
        bw = w * img_w * self._scale
        bh = h * img_h * self._scale
        rect = QRect(int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh))
        if rect.contains(pos):
            return idx
    return -1
```

**`__init__` 中初始化新属性**（在 `self._on_box_drawn_cb = None` 之后）：

```python
self._on_box_drawn_cb = None
self._on_box_clicked_cb = None
self._on_clear_selection_cb = None
```

---

#### 改动 6：Dialog 注册画布回调 + 实现取消选中

**位置**：在 `self.canvas.set_on_box_drawn(self._on_box_drawn)` 之后（[L348](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L348)）

```python
self.canvas.set_on_box_drawn(self._on_box_drawn)
self.canvas.set_on_box_clicked(self._on_box_clicked)
self.canvas.set_on_clear_selection(self._on_clear_selection)
```

**新增方法**（在 `_on_box_selected` 附近）：

```python
def _on_box_clicked(self, idx):
    """画布点击已有框时，同步选中右栏列表"""
    self.box_list.setCurrentRow(idx)

def _on_clear_selection(self):
    """画布点击空白处时，取消选中右栏列表"""
    self.box_list.setCurrentRow(-1)
```

**注意**：`box_list.setCurrentRow(-1)` 会触发 `currentRowChanged(-1)` → `_on_box_selected(-1)` → `btn_modify.setEnabled(False)`，自动完成按钮变灰。

---

#### 改动 7：移除 `_on_class_changed` 的自动修改逻辑

**位置**：修改 [L557-L575](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L557-L575)

**原因**：原 `_on_class_changed` 在切换类别时自动修改选中框的类别。现在有了"修改"按钮，类别修改应统一走"修改"按钮，避免行为混乱。

```python
def _on_class_changed(self):
    """类别下拉切换时：仅更新状态栏和提示（不自动改选中框，需点"修改"）"""
    self._update_quick_hint()
    if self.canvas._quick_mode:
        cls = self.combo_class.currentText()
        self.status_bar.showMessage(f"快速标注模式: 开启 | 类别: {cls}")
```

---

## Assumptions & Decisions

1. **"修改"按钮初始禁用**：`setEnabled(False)`，灰色不可点。
2. **选中联动**：右栏 `box_list.currentRow >= 0` → 启用；`= -1` → 禁用。
3. **画布点击空白取消选中**：在快速模式下，点击画布空白处（非任何已有框内）触发 `box_list.setCurrentRow(-1)`，按钮变灰。
4. **画布点击已有框选中**：在快速模式下，点击已有框内 → 选中该框（不开始画新框），按钮亮起。这是对用户思路第 4 点的补充——让"点击非标签位置取消选中"更完整，因为点击框内也应选中对应框。
5. **类别修改走"修改"按钮**：移除 `_on_class_changed` 的自动修改逻辑，所有参数修改（类别 + 坐标）统一通过"修改"按钮提交，行为清晰一致。
6. **修改后保持选中**：`_on_modify_box` 修改后会 `setCurrentRow(row)` 重新选中，保持选中状态，方便连续调整。
7. **非快速模式下点击画布无反应**：保持现状，画布点击选中/取消选中只在快速模式下生效。这是合理的，因为非快速模式下用户主要在右栏列表操作。
8. **"添加"按钮不清除选中**：添加新框后，选中状态不变（仍选中原有的框）。如果想选中新框，可在右栏手动点击。

## Verification Steps

1. **语法检查**：
   ```
   python -m py_compile app/ui/label_editor_dialog.py
   ```

2. **"修改"按钮初始状态**：打开窗口 → "修改"按钮应为灰色不可点。

3. **选中标注框后按钮亮起**：
   - 右栏列表点击某个标注框 → "修改"按钮变亮可点。
   - 类别下拉框和 xc/yc/w/h 自动填入选中框的数据。

4. **修改参数**：
   - 选中一个框 → 修改 xc/yc/w/h（如 xc 改为 0.6）→ 点"修改" → 右栏列表对应行的文字更新为 `xc=0.600`，画布红框位置移动。
   - 修改类别下拉框 → 点"修改" → 右栏列表对应行的类别名更新。

5. **取消选中按钮变灰**：
   - 选中一个框 → 按 Ctrl+点击右栏空白处（或用代码触发 `setCurrentRow(-1)`）→ "修改"按钮变灰。
   - **快速模式下**：选中一个框 → 在画布空白处点击 → 右栏取消选中，"修改"按钮变灰，开始画新框。

6. **画布点击已有框选中**（快速模式下）：
   - 选中框 A → 在画布上点击框 B → 右栏选中切换到框 B，"修改"按钮保持亮起，输入区同步框 B 的数据。

7. **切换类别不再自动改框**：
   - 选中框 A（类别 smoke）→ 切换类别下拉框到 smoke2 → 右栏列表框 A 的类别**不变**（仍为 smoke）→ 点"修改" → 框 A 类别才变为 smoke2。
