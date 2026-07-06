# 标注编辑器功能增强：Q键快速标注 + 类别可添加

## Summary

在已运行的 `LabelEditorDialog` 上做三项增强：
1. **左下角提示行**：在左栏图片列表下方加一行灰色提示"使用 Q 键和鼠标进行快速标注"。
2. **Q键快速标注模式**：按 Q 键切换"快速标注模式"。开启时画布进入拉框模式，鼠标拖动即可在图片上画框添加标签，**默认使用下拉框当前选中的类别**。再按 Q 退出。
3. **手动输入区类别可添加**：在类别下拉框旁加"+"按钮，弹输入框新增类别，**持久化写入** `configs/predefined_classes.txt`，下次打开仍可用。

## Current State Analysis

### 当前实现（基于 Phase 1 探索 [app/ui/label_editor_dialog.py](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py)）

- **AnnotationCanvas**：已实现 `mousePress/Move/Release` 拖拽画框，松开时回调 `parent._on_box_drawn(xc, yc, w, h)`。当前是"鼠标按下即开始画框"，没有模式开关。
- **LabelEditorDialog**：
  - 左栏（[L280-L295](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L280-L295)）：图片列表 + 上一张/下一张按钮。
  - 中栏手动输入区（[L310-L351](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L310-L351)）：`combo_class` QComboBox + 4 个 QDoubleSpinBox + 添加按钮。
  - `_on_box_drawn`（[L449-L458](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L449-L458)）：用 `self.combo_class.currentIndex()` 作为 class_id。
  - 类别加载 `_load_class_names`（[L255-L265](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L255-L265)）：从 `configs/predefined_classes.txt` 读取。
- **类别文件** [configs/predefined_classes.txt](file:///e:/project/Dusc%20AI%20CV%20GPU/configs/predefined_classes.txt)：当前只有 `smoke`。

### 关键发现

当前 `mousePressEvent` 无条件开始画框。这意味着**任何鼠标左键按下都会画框**——这与 Q 键模式切换存在冲突。需要改为：只有"快速标注模式开启"时才响应鼠标画框。

## Proposed Changes

### 改动文件

**`e:\project\Dusc AI CV GPU\app\ui\label_editor_dialog.py`**

---

#### 改动 1：AnnotationCanvas 增加"模式开关"

**1a. 新增实例属性**（[__init__ L18-L35](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L18-L35)）

在 `self._scale = 1.0` 之后追加：
```python
self._quick_mode = False  # Q键快速标注模式开关
```

**1b. 新增 set_quick_mode 方法**（在 `set_class_names` 之后）

```python
def set_quick_mode(self, enabled):
    """开启/关闭快速标注模式"""
    self._quick_mode = bool(enabled)
    if not enabled:
        # 退出时取消正在拉的框
        self._drawing = False
        self._start_point = None
        self._end_point = None
    # 改变鼠标光标
    if self._quick_mode:
        self.setCursor(Qt.CrossCursor)
    else:
        self.unsetCursor()
    self.update()
```

**1c. 修改 paintEvent**（[L120-L169](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L120-L169)）

在 `paintEvent` 末尾（画完正在拉的框之后）追加：画出"快速模式开启"的边框提示：

```python
# 快速模式开启时画绿色边框
if self._quick_mode:
    pen = QPen(QColor(0, 180, 0), 3)
    painter.setPen(pen)
    painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
```

**1d. 修改 mousePressEvent**（[L173-L178](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L173-L178)）

```python
def mousePressEvent(self, event):
    # 只有快速模式开启才响应画框
    if not self._quick_mode:
        return
    if event.button() != Qt.LeftButton or not self._pixmap:
        return
    self._drawing = True
    self._start_point = event.pos()
    self._end_point = event.pos()
```

**1e. 修改 mouseMoveEvent**（[L180-L184](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L180-L184)）

```python
def mouseMoveEvent(self, event):
    if not self._quick_mode or not self._drawing:
        return
    self._end_point = event.pos()
    self.update()
```

**1f. 修改 mouseReleaseEvent**（[L186-L229](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L186-L229)）

在开头加 `if not self._quick_mode: return`：

```python
def mouseReleaseEvent(self, event):
    if not self._quick_mode:
        return
    if event.button() != Qt.LeftButton or not self._drawing:
        return
    # ...（保持原逻辑不变）
```

---

#### 改动 2：LabelEditorDialog 增加 Q 键监听 + 左下角提示

**2a. 重写 keyPressEvent**（在 `_setup_ui` 之后新增方法）

```python
def keyPressEvent(self, event):
    """Q 键切换快速标注模式"""
    if event.key() == Qt.Key_Q:
        self._toggle_quick_mode()
        return
    # 其他按键走默认处理（如 Esc 关闭）
    super().keyPressEvent(event)

def _toggle_quick_mode(self):
    new_state = not self.canvas._quick_mode
    self.canvas.set_quick_mode(new_state)
    if new_state:
        cls = self.combo_class.currentText()
        self.status_bar.showMessage(f"快速标注模式: 开启 | 类别: {cls}")
    else:
        self.status_bar.showMessage("快速标注模式: 关闭")
    self._update_quick_hint()

def _update_quick_hint(self):
    """更新左下角提示文字"""
    if self.canvas._quick_mode:
        self.hint_label.setText("● 快速标注模式: 开启（按 Q 退出）| 类别: " + self.combo_class.currentText())
        self.hint_label.setStyleSheet("QLabel { color: #2a7d2a; font-weight: bold; }")
    else:
        self.hint_label.setText("使用 Q 键和鼠标进行快速标注")
        self.hint_label.setStyleSheet("QLabel { color: #888888; }")
```

**2b. 左栏底部加提示行**（修改 [_setup_ui L287-L294](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L287-L294)）

在 `nav_row` 之后、`splitter.addWidget(left_group)` 之前插入：

```python
nav_row = QHBoxLayout()
self.btn_prev = QPushButton("上一张")
self.btn_prev.clicked.connect(self._on_prev)
self.btn_next = QPushButton("下一张")
self.btn_next.clicked.connect(self._on_next)
nav_row.addWidget(self.btn_prev)
nav_row.addWidget(self.btn_next)
left_layout.addLayout(nav_row)

# 左下角提示
self.hint_label = QLabel("使用 Q 键和鼠标进行快速标注")
self.hint_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
self.hint_label.setWordWrap(True)
left_layout.addWidget(self.hint_label)

splitter.addWidget(left_group)
```

---

#### 改动 3：手动输入区类别可添加 + 持久化

**3a. 类别行布局改造**（修改 [_setup_ui L312-L315](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L312-L315)）

把单独的 `combo_class` 改成"下拉框 + 添加按钮"的水平布局：

```python
# 类别行：下拉框 + 添加按钮
class_row = QHBoxLayout()
self.combo_class = QComboBox()
for name in self._class_names:
    self.combo_class.addItem(name)
self.combo_class.currentIndexChanged.connect(self._on_class_changed)
class_row.addWidget(self.combo_class, 1)

self.btn_add_class = QPushButton("+")
self.btn_add_class.setFixedWidth(28)
self.btn_add_class.setToolTip("添加新类别")
self.btn_add_class.clicked.connect(self._on_add_class)
class_row.addWidget(self.btn_add_class)
manual_form.addRow("类别:", class_row)
```

**3b. 新增 _on_add_class 方法**

```python
def _on_add_class(self):
    """添加新类别，持久化到 configs/predefined_classes.txt"""
    name, ok = QInputDialog.getText(self, "添加类别", "请输入新类别名称:")
    if not ok or not name.strip():
        return
    name = name.strip()
    # 去重
    if name in self._class_names:
        QMessageBox.information(self, "提示", f"类别 '{name}' 已存在")
        return
    # 加入内存列表
    self._class_names.append(name)
    self.combo_class.addItem(name)
    self.combo_class.setCurrentIndex(len(self._class_names) - 1)
    # 同步到画布的 class_names
    self.canvas.set_class_names(self._class_names)
    # 持久化到文件
    self._save_class_names()
    self.status_bar.showMessage(f"已添加类别: {name}")

def _save_class_names(self):
    """把当前类别列表写回 configs/predefined_classes.txt"""
    classes_file = self.project_root / "configs" / "predefined_classes.txt"
    classes_file.parent.mkdir(parents=True, exist_ok=True)
    with open(classes_file, "w", encoding="utf-8") as f:
        for name in self._class_names:
            f.write(name + "\n")

def _on_class_changed(self):
    """类别下拉切换时更新状态栏和提示"""
    self._update_quick_hint()
    if self.canvas._quick_mode:
        cls = self.combo_class.currentText()
        self.status_bar.showMessage(f"快速标注模式: 开启 | 类别: {cls}")
```

**3c. 导入 QInputDialog**

修改文件顶部导入（[L7-L12](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L7-L12)）：

```python
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QGroupBox, QFormLayout, QComboBox, QDoubleSpinBox, QMessageBox,
    QScrollArea, QSizePolicy, QFrame, QStatusBar, QInputDialog
)
```

---

## Assumptions & Decisions

1. **Q键模式切换**：按 Q 进入快速标注模式（鼠标拖动画框），再按 Q 退出。这是符合"labelImg 风格"的标准做法。**默认进入窗口时模式关闭**——避免用户误操作，且让"提示文字"有意义。
2. **类别持久化**：新增类别写入 `configs/predefined_classes.txt`，下次打开窗口仍可用。这也意味着训练时 YOLO 会读到最新类别。
3. **快速模式默认类别**：使用 `combo_class` 当前选中项（满足需求 3"默认使用标签类别当前的标签类别"）。切换类别时自动更新。
4. **不删除原有类别**：只允许新增，不提供删除类别功能（避免误删导致已有标签 class_id 错乱）。
5. **Q 键只在窗口聚焦时生效**：用 QDialog 的 `keyPressEvent`，子控件聚焦时 Qt 会先派发给子控件，但 QListWidget/QComboBox 一般不消费 Q 键，所以能冒泡到 dialog。如果发现 QListWidget 聚焦时 Q 不生效，后续可加 `QShortcut` 全局监听。
6. **画布绿色边框**：快速模式开启时画布边缘显示绿色边框，让用户清楚知道当前状态。
7. **光标变化**：快速模式开启时鼠标变成十字光标 `CrossCursor`，退出时恢复默认。
8. **类别去重**：新增同名类别弹提示"已存在"，不重复添加。
9. **空类别名**：trim 后为空则忽略。

## Verification Steps

1. **语法检查**：
   ```
   python -m py_compile app/ui/label_editor_dialog.py
   ```

2. **左下角提示**：运行 GUI → 数据管理页 → 点"添加标签" → 窗口左下角应显示灰色文字"使用 Q 键和鼠标进行快速标注"。

3. **Q键切换**：
   - 默认状态：鼠标在画布上拖动**无反应**（模式关闭）。
   - 按 Q 键：左下角提示变成绿色"● 快速标注模式: 开启（按 Q 退出）| 类别: smoke"，画布出现绿色边框，鼠标变十字光标。
   - 鼠标拖动画框：松开后红框出现，右栏列表新增一行。
   - 按 Q 键退出：提示恢复灰色，画布边框消失，鼠标拖动无反应。

4. **默认类别**：
   - 在下拉框选中某个类别（如 smoke）→ 按 Q → 画框 → 右栏显示的类别名与下拉框一致。
   - 切换下拉框到另一类别 → 状态栏和左下角提示应更新类别名 → 再画框用新类别。

5. **类别添加**：
   - 类别下拉框右侧应有"+"按钮。
   - 点"+" → 弹输入框 → 输入 "fire" → 确定 → 下拉框自动选中 "fire"。
   - 重复添加 "fire" → 弹"已存在"提示。
   - 用记事本打开 `configs/predefined_classes.txt` → 应包含 `smoke` 和 `fire` 两行。
   - 关闭窗口重新打开 → 下拉框应仍有 "fire"。

6. **拉框后右栏显示**：画框后右栏新增一行，类别名（如 `smoke`）正确显示在前面。

7. **保存验证**：画几个框 → 保存 → 用记事本打开 `resource/labels/<stem>.txt` → 第一列 class_id 与下拉框顺序一致（smoke=0, fire=1）。
