# 修复预览区随浏览不断变大的 Bug

## 问题现象

在数据管理页连续点击左侧图片素材（从第 1 张看到最后一张）时，中间的**预览区会越来越大**，逐步蚕食左栏素材列表和右栏媒体信息的空间。

## 根本原因分析

预览区 `preview_label` 是一个 `QLabel`，位于 `QSplitter` 的中间分栏。当前代码（[data_page.py#L101-L107](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L101-L107)）：

```python
self.preview_label = QLabel("请选择左侧素材进行预览")
self.preview_label.setAlignment(Qt.AlignCenter)
self.preview_label.setMinimumSize(480, 360)
self.preview_label.setStyleSheet(
    "QLabel { border: 1px solid #cccccc; background-color: #fafafa; color: #888888; }"
)
```

**问题链条（正反馈循环）**：

1. `QLabel` 默认的 `sizePolicy` 是 `(Preferred, Preferred)`，其 `sizeHint()` 会跟随内容（pixmap/text）变化。
2. `_show_preview` 中执行（[data_page.py#L262-L267](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L262-L267)）：
   ```python
   scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
   self.preview_label.setPixmap(scaled)
   ```
   缩放目标用的是 `preview_label.size()`——即 label 当前的实际尺寸。
3. `setPixmap(scaled)` 后，QLabel 的 `sizeHint()` 变成 scaled pixmap 的大小（接近 label 当前 size）。
4. 在 `QSplitter` 中，widget 的 `sizeHint()` 增大会触发 splitter 重新分配空间——给预览区更多像素。
5. 下次用户点新图片时，`self.preview_label.size()` 已经变大 → scaled 出更大的图 → `sizeHint()` 更大 → splitter 再分配更多空间……
6. 每浏览一张图片，预览区就胀大一格，形成**正反馈循环**。

辅助证据：项目里另一个 `app/widgets/media_preview.py` 用相同模式（`scaled(preview_label.size())` + `setPixmap` + splitter），存在同样隐患，但本次只修用户实际使用的 data_page。

## 修复方案

在 `_setup_ui` 中给 `preview_label` 设置 `sizePolicy` 为 `Ignored`，让 QLabel 的 `sizeHint()` **不参与** splitter 的空间分配，从而切断正反馈循环。

### 改动文件

**`e:\project\Dusc AI CV GPU\app\ui\data_page.py`**

#### 改动 1：导入 QSizePolicy

第 2-6 行的 PyQt5.QtWidgets 导入末尾追加 `QSizePolicy`：

```python
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QInputDialog, QListWidget, QListWidgetItem,
    QSplitter, QGroupBox, QLabel, QAbstractItemView, QMenu, QAction,
    QProgressBar, QDialog, QFormLayout, QSpinBox, QDialogButtonBox,
    QRadioButton, QButtonGroup, QFrame, QSizePolicy)
```

#### 改动 2：preview_label 设置 sizePolicy

在 [data_page.py#L101-L107](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/data_page.py#L101-L107) 的 `setMinimumSize` 之后、`setStyleSheet` 之前插入一行：

```python
self.preview_label = QLabel("请选择左侧素材进行预览")
self.preview_label.setAlignment(Qt.AlignCenter)
self.preview_label.setMinimumSize(480, 360)
self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)  # 新增：阻止 sizeHint 反馈循环
self.preview_label.setStyleSheet(
    "QLabel { border: 1px solid #cccccc; background-color: #fafafa; color: #888888; }"
)
```

### 为什么选 `Ignored` 而不是其他策略

| 策略 | 效果 | 是否合适 |
|------|------|---------|
| `Preferred`（默认） | sizeHint 影响 splitter 分配 → 正反馈 | ❌ 当前 bug |
| `Fixed` | 固定 sizeHint，但会锁死不让 splitter 调整 | ❌ 太严格 |
| `Minimum` | sizeHint 作为下限，仍会增长 | ❌ 无法修复 |
| `Maximum` | sizeHint 作为上限，方向不对 | ❌ |
| **`Ignored`** | sizeHint 被忽略，splitter 完全按 stretch factor 分配 | ✅ |

`Ignored` 的官方含义：widget 的 `sizeHint()` 被 splitter 忽略，空间分配完全由 `setStretchFactor` 决定。`setMinimumSize(480, 360)` 仍保证最小可见尺寸，`resizeEvent` 中的重缩放仍正常工作——预览区尺寸由 splitter 比例决定，**不再受 pixmap 内容影响**。

## Assumptions & Decisions

1. **只修 data_page.py，不动 media_preview.py**：用户报告的是数据管理页的预览区；`media_preview.py` 是早期 demo 组件，当前未被 main_window 使用（DataPage 是独立实现），本次不扩大改动范围。
2. **不改缩放逻辑**：仍用 `preview_label.size()` 作为缩放目标——这是正确的（按当前可见尺寸缩放）。bug 在于 sizeHint 反馈，不在缩放本身。
3. **保留 `setMinimumSize(480, 360)`**：保证初始可见性，避免 label 在 splitter 初始布局时被压成 0。
4. **保留 `resizeEvent` 重缩放逻辑**：窗口 resize 时重新按新 size 缩放 pixmap，行为正确。
5. **不设置 `setMaximumSize`**：用 sizePolicy 治本，不用 max size 治标。

## Verification Steps

1. **语法检查**：
   ```
   python -m py_compile app/ui/data_page.py
   ```
2. **运行 GUI**：`run.bat` 启动应用，切到"数据管理"页。
3. **复现验证（修复前应复现，修复后应消失）**：
   - 确保左侧图片素材列表有 ≥ 10 张图片
   - 用键盘 ↓ 键从第 1 张连续按到最后一张
   - 观察：预览区尺寸应**保持不变**，左栏素材列表和右栏媒体信息宽度不被蚕食
4. **resize 验证**：手动拖动 splitter 分隔条，预览区应能自由调整；拖动窗口边框，预览区应按比例缩放，且图片仍正确铺满预览区。
5. **切换素材类型**：依次点视频 → 图片 → 标签，预览区尺寸稳定，不因切换内容类型而变化。
