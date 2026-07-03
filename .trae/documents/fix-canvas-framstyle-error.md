# 修复 AnnotationCanvas 的 setFrameStyle 错误

## 问题

运行时报错：
```
AttributeError: 'AnnotationCanvas' object has no attribute 'setFrameStyle'
```

位置：[app/ui/label_editor_dialog.py:35](file:///e:/project/Dusc%20AI%20CV%20GPU/app/ui/label_editor_dialog.py#L35)

## 根本原因

`AnnotationCanvas(QWidget)` 继承自 `QWidget`，但调用了 `self.setFrameStyle(QFrame.Box | QFrame.Plain)`。`setFrameStyle` 是 `QFrame` 类的方法，`QWidget` 没有该方法。

## 修复方案

移除该行，改用 `setStyleSheet` 设置边框。两种等价做法中选简单的一种。

### 改动文件

**`e:\project\Dusc AI CV GPU\app\ui\label_editor_dialog.py`** 第 33-36 行

#### 当前代码
```python
self.setMinimumSize(480, 360)
self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
self.setFrameStyle(QFrame.Box | QFrame.Plain)
```

#### 修复后
```python
self.setMinimumSize(480, 360)
self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
self.setStyleSheet("QWidget { border: 1px solid #cccccc; }")
```

### 为什么不改为继承 QFrame

- `QFrame` 是 `QWidget` 的子类，改继承后 `paintEvent` 等仍可正常工作
- 但 `QFrame` 默认会绘制自己的边框，可能干扰 `paintEvent` 中的 `fillRect(self.rect(), ...)` 背景
- 用 `setStyleSheet` 最小改动，行为可控，不影响现有 paint 逻辑
- `QFrame` 仍需在导入中保留（用于 `QFrame` 类型引用，但本文件未在其他地方使用 QFrame 类型，可一并清理导入——但为最小改动，仅注释掉那行不可用调用）

## Assumptions & Decisions

1. **最小改动**：只改一行，不调整继承结构。
2. **保留 QFrame 导入**：虽然不再调用 `setFrameStyle`，但 `QFrame` 导入无害，避免连带修改导入行。
3. **边框样式**：用 1px 灰色边框，与原 `QFrame.Box | QFrame.Plain` 视觉接近。

## Verification Steps

1. **语法检查**：
   ```
   python -m py_compile app/ui/label_editor_dialog.py
   ```
2. **运行 GUI**：`run.bat` → 数据管理页 → 点"添加标签"按钮 → 窗口应正常弹出，画布周围有灰色边框，无 AttributeError。
3. **画布功能**：图片加载、鼠标拉框、标注框显示均正常。
