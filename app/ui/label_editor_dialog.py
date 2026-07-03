"""标签标注窗口：内置 labelImg 风格的 YOLO 标注编辑器"""

from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QPoint, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QListWidget, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QGroupBox, QFormLayout, QComboBox, QDoubleSpinBox, QMessageBox,
    QScrollArea, QSizePolicy, QFrame, QStatusBar
)


class AnnotationCanvas(QWidget):
    """标注画布：显示图片 + 已有标注框 + 当前拉框，支持鼠标拖拽画框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None            # 原始 QPixmap
        self._image_path = None        # 当前图片路径
        self._boxes = []               # list of (class_id, xc, yc, w, h) 归一化
        self._class_names = []         # 类别列表
        self._selected_index = -1      # 选中的标注框索引
        # 拉框状态
        self._drawing = False
        self._start_point = None       # 画布上的起点（像素）
        self._end_point = None         # 画布上的终点（像素）
        # 图片显示缩放：画布上实际显示尺寸 / 图片原始尺寸
        self._scale = 1.0

        self.setMouseTracking(True)
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("QWidget { border: 1px solid #cccccc; }")

    def set_class_names(self, names):
        self._class_names = names

    def load_image(self, image_path, boxes):
        """加载图片及其标注框"""
        self._image_path = Path(image_path)
        self._pixmap = QPixmap(str(self._image_path))
        self._boxes = list(boxes) if boxes else []
        self._selected_index = -1
        self._drawing = False
        self._start_point = None
        self._end_point = None
        self.update()

    def set_boxes(self, boxes):
        """更新标注框列表（外部调用）"""
        self._boxes = list(boxes) if boxes else []
        self.update()

    def set_selected(self, index):
        """设置高亮的标注框"""
        self._selected_index = index
        self.update()

    def get_boxes(self):
        return list(self._boxes)

    def add_box(self, class_id, xc, yc, w, h):
        """添加一个标注框，返回索引"""
        self._boxes.append((class_id, xc, yc, w, h))
        self.update()
        return len(self._boxes) - 1

    def remove_box(self, index):
        """删除指定索引的标注框"""
        if 0 <= index < len(self._boxes):
            del self._boxes[index]
            if self._selected_index == index:
                self._selected_index = -1
            elif self._selected_index > index:
                self._selected_index -= 1
            self.update()

    def clear_boxes(self):
        self._boxes = []
        self._selected_index = -1
        self.update()

    # ---------- 坐标转换 ----------

    def _compute_scale(self):
        """计算图片在画布上的缩放比，保持长宽比"""
        if not self._pixmap or self._pixmap.isNull():
            self._scale = 1.0
            return
        cw = max(self.width() - 4, 1)
        ch = max(self.height() - 4, 1)
        iw = self._pixmap.width()
        ih = self._pixmap.height()
        if iw <= 0 or ih <= 0:
            self._scale = 1.0
            return
        self._scale = min(cw / iw, ch / ih)

    def _image_offset(self):
        """图片左上角在画布上的像素位置"""
        if not self._pixmap or self._pixmap.isNull():
            return QPoint(0, 0)
        iw = int(self._pixmap.width() * self._scale)
        ih = int(self._pixmap.height() * self._scale)
        x = (self.width() - iw) // 2
        y = (self.height() - ih) // 2
        return QPoint(x, y)

    def _canvas_to_image(self, canvas_pt):
        """画布像素 → 图片原始像素"""
        offset = self._image_offset()
        ix = (canvas_pt.x() - offset.x()) / max(self._scale, 1e-9)
        iy = (canvas_pt.y() - offset.y()) / max(self._scale, 1e-9)
        return ix, iy

    # ---------- 绘制 ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 背景
        painter.fillRect(self.rect(), QColor(245, 245, 245))

        if not self._pixmap or self._pixmap.isNull():
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "无图片")
            return

        self._compute_scale()
        offset = self._image_offset()
        iw = int(self._pixmap.width() * self._scale)
        ih = int(self._pixmap.height() * self._scale)

        # 画图片
        painter.drawPixmap(offset.x(), offset.y(), iw, ih, self._pixmap)

        # 画已有标注框
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()
        pen_normal = QPen(QColor(255, 0, 0), 2)
        pen_selected = QPen(QColor(0, 120, 255), 3)
        font = QFont("Arial", 10)
        font.setBold(True)
        painter.setFont(font)

        for idx, (cid, xc, yc, bw, bh) in enumerate(self._boxes):
            # 归一化 → 画布像素
            cx = offset.x() + xc * img_w * self._scale
            cy = offset.y() + yc * img_h * self._scale
            w = bw * img_w * self._scale
            h = bh * img_h * self._scale
            rect = QRect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
            if idx == self._selected_index:
                painter.setPen(pen_selected)
            else:
                painter.setPen(pen_normal)
            painter.drawRect(rect)
            # 类别文字
            name = self._class_names[cid] if 0 <= cid < len(self._class_names) else str(cid)
            painter.drawText(rect.topLeft() - QPoint(0, 4), name)

        # 画当前正在拉的框
        if self._drawing and self._start_point and self._end_point:
            pen = QPen(QColor(0, 200, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            r = QRect(self._start_point, self._end_point).normalized()
            painter.drawRect(r)

    # ---------- 鼠标事件 ----------

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or not self._pixmap:
            return
        self._drawing = True
        self._start_point = event.pos()
        self._end_point = event.pos()

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._end_point = event.pos()
            self.update()
        # 状态栏可通过 parent 更新（这里不直接处理，由 dialog 监听）

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._drawing:
            return
        self._drawing = False
        self._end_point = event.pos()
        self.update()

        if not self._start_point or not self._end_point:
            return
        # 矩形必须足够大
        rect = QRect(self._start_point, self._end_point).normalized()
        if rect.width() < 3 or rect.height() < 3:
            self._start_point = None
            self._end_point = None
            return

        # 画布像素 → 图片原始像素 → 归一化
        offset = self._image_offset()
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()
        x1 = (rect.left() - offset.x()) / max(self._scale, 1e-9)
        y1 = (rect.top() - offset.y()) / max(self._scale, 1e-9)
        x2 = (rect.right() - offset.x()) / max(self._scale, 1e-9)
        y2 = (rect.bottom() - offset.y()) / max(self._scale, 1e-9)
        # 裁剪到图片范围
        x1 = max(0, min(x1, img_w))
        x2 = max(0, min(x2, img_w))
        y1 = max(0, min(y1, img_h))
        y2 = max(0, min(y2, img_h))
        if x2 - x1 < 2 or y2 - y1 < 2:
            self._start_point = None
            self._end_point = None
            return
        xc = ((x1 + x2) / 2) / img_w
        yc = ((y1 + y2) / 2) / img_h
        w = (x2 - x1) / img_w
        h = (y2 - y1) / img_h

        self._start_point = None
        self._end_point = None

        # 通知 dialog 处理（拉框完成）
        if hasattr(self.parent(), '_on_box_drawn'):
            self.parent()._on_box_drawn(xc, yc, w, h)


class LabelEditorDialog(QDialog):
    """标签标注窗口：管理图片和标签，支持鼠标拉框 + 手动输入"""

    def __init__(self, project_root, dataset_manager, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.dataset_manager = dataset_manager
        # 当前所有图片素材（MediaInfo 列表）
        self._images = [m for m in self.dataset_manager.list_media() if m.media_type == "image"]
        # 每张图片的当前标注框 dict: image_name -> list of (cid, xc, yc, w, h)
        self._boxes_map = {}
        # 每张图片是否已修改
        self._dirty = set()
        # 类别列表
        self._class_names = self._load_class_names()
        # 当前图片
        self._current_image = None

        self._setup_ui()
        self._load_image_list()

    # ---------- 初始化 ----------

    def _load_class_names(self):
        classes_file = self.project_root / "configs" / "predefined_classes.txt"
        if not classes_file.exists():
            return ["smoke"]
        names = []
        with open(classes_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    names.append(line)
        return names if names else ["smoke"]

    def _setup_ui(self):
        self.setWindowTitle("标注编辑器")
        self.setMinimumSize(1100, 720)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 三栏 splitter
        splitter = QSplitter(Qt.Horizontal)

        # === 左栏：图片列表 ===
        left_group = QGroupBox("图片列表")
        left_layout = QVBoxLayout(left_group)
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SingleSelection)
        self.image_list.currentRowChanged.connect(self._on_image_changed)
        left_layout.addWidget(self.image_list, 1)

        nav_row = QHBoxLayout()
        self.btn_prev = QPushButton("上一张")
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next = QPushButton("下一张")
        self.btn_next.clicked.connect(self._on_next)
        nav_row.addWidget(self.btn_prev)
        nav_row.addWidget(self.btn_next)
        left_layout.addLayout(nav_row)
        splitter.addWidget(left_group)

        # === 中栏：画布 + 手动输入 ===
        mid_group = QGroupBox("画布")
        mid_layout = QVBoxLayout(mid_group)

        self.canvas = AnnotationCanvas(self)
        self.canvas.set_class_names(self._class_names)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.canvas)
        scroll.setMinimumHeight(420)
        mid_layout.addWidget(scroll, 1)

        # 手动输入区
        manual_group = QGroupBox("手动输入（YOLO 归一化坐标）")
        manual_form = QFormLayout(manual_group)
        self.combo_class = QComboBox()
        for name in self._class_names:
            self.combo_class.addItem(name)
        manual_form.addRow("类别:", self.combo_class)

        coord_row1 = QHBoxLayout()
        self.spin_xc = QDoubleSpinBox()
        self.spin_xc.setRange(0.0, 1.0)
        self.spin_xc.setSingleStep(0.001)
        self.spin_xc.setDecimals(3)
        self.spin_yc = QDoubleSpinBox()
        self.spin_yc.setRange(0.0, 1.0)
        self.spin_yc.setSingleStep(0.001)
        self.spin_yc.setDecimals(3)
        coord_row1.addWidget(QLabel("xc:"))
        coord_row1.addWidget(self.spin_xc)
        coord_row1.addWidget(QLabel("yc:"))
        coord_row1.addWidget(self.spin_yc)
        manual_form.addRow(coord_row1)

        coord_row2 = QHBoxLayout()
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0.0, 1.0)
        self.spin_w.setSingleStep(0.001)
        self.spin_w.setDecimals(3)
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0.0, 1.0)
        self.spin_h.setSingleStep(0.001)
        self.spin_h.setDecimals(3)
        coord_row2.addWidget(QLabel("w:"))
        coord_row2.addWidget(self.spin_w)
        coord_row2.addWidget(QLabel("h:"))
        coord_row2.addWidget(self.spin_h)
        manual_form.addRow(coord_row2)

        self.btn_add_manual = QPushButton("添加")
        self.btn_add_manual.clicked.connect(self._on_add_manual)
        manual_form.addRow(self.btn_add_manual)

        mid_layout.addWidget(manual_group)
        splitter.addWidget(mid_group)

        # === 右栏：标注框列表 ===
        right_group = QGroupBox("标注框")
        right_layout = QVBoxLayout(right_group)
        self.box_list = QListWidget()
        self.box_list.setSelectionMode(QListWidget.SingleSelection)
        self.box_list.currentRowChanged.connect(self._on_box_selected)
        right_layout.addWidget(self.box_list, 1)

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.clicked.connect(self._on_delete_box)
        right_layout.addWidget(self.btn_delete)

        self.btn_clear = QPushButton("清空全部")
        self.btn_clear.clicked.connect(self._on_clear_boxes)
        right_layout.addWidget(self.btn_clear)
        splitter.addWidget(right_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([220, 640, 220])
        layout.addWidget(splitter, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪")
        layout.addWidget(self.status_bar)

        # 底部按钮
        btn_row = QHBoxLayout()
        self.btn_save_current = QPushButton("保存当前")
        self.btn_save_current.clicked.connect(self._on_save_current)
        self.btn_save_all = QPushButton("保存全部并关闭")
        self.btn_save_all.clicked.connect(self._on_save_all)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_save_current)
        btn_row.addWidget(self.btn_save_all)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    # ---------- 图片列表 ----------

    def _load_image_list(self):
        self.image_list.clear()
        for i, m in enumerate(self._images, 1):
            item = QListWidgetItem(f"{i:03d}. {m.name}")
            item.setData(Qt.UserRole, m)
            self.image_list.addItem(item)
        if self._images:
            self.image_list.setCurrentRow(0)

    def _on_image_changed(self, row):
        if row < 0 or row >= len(self._images):
            return
        # 切换前先保存当前图片的标注到内存（不写文件）
        # （canvas.get_boxes() 在 load_image 后会丢失，所以在 _save_current_to_map 中维护）
        m = self._images[row]
        self._current_image = m
        # 加载已有标注框
        boxes = self._load_boxes_for_image(m.name)
        self._boxes_map[m.name] = list(boxes)
        # 加载图片到画布
        img_path = self._resolve_path(m.path)
        self.canvas.load_image(img_path, boxes)
        self._refresh_box_list()
        self._update_status()

    def _on_prev(self):
        row = self.image_list.currentRow()
        if row > 0:
            self.image_list.setCurrentRow(row - 1)

    def _on_next(self):
        row = self.image_list.currentRow()
        if 0 <= row < self.image_list.count() - 1:
            self.image_list.setCurrentRow(row + 1)

    # ---------- 标注框列表 ----------

    def _refresh_box_list(self):
        self.box_list.clear()
        if not self._current_image:
            return
        boxes = self._boxes_map.get(self._current_image.name, [])
        for i, (cid, xc, yc, w, h) in enumerate(boxes):
            name = self._class_names[cid] if 0 <= cid < len(self._class_names) else str(cid)
            text = f"{name}  xc={xc:.3f} yc={yc:.3f} w={w:.3f} h={h:.3f}"
            self.box_list.addItem(text)
        self.canvas.set_boxes(boxes)

    def _on_box_selected(self, row):
        self.canvas.set_selected(row)

    def _on_box_drawn(self, xc, yc, w, h):
        """AnnotationCanvas 拉框完成时回调"""
        if not self._current_image:
            return
        cid = self.combo_class.currentIndex()
        boxes = self._boxes_map.setdefault(self._current_image.name, [])
        boxes.append((cid, xc, yc, w, h))
        self._dirty.add(self._current_image.name)
        self._refresh_box_list()
        self._update_status()

    def _on_add_manual(self):
        if not self._current_image:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        xc = self.spin_xc.value()
        yc = self.spin_yc.value()
        w = self.spin_w.value()
        h = self.spin_h.value()
        if w <= 0 or h <= 0:
            QMessageBox.warning(self, "提示", "宽度和高度必须大于 0")
            return
        cid = self.combo_class.currentIndex()
        boxes = self._boxes_map.setdefault(self._current_image.name, [])
        boxes.append((cid, xc, yc, w, h))
        self._dirty.add(self._current_image.name)
        self._refresh_box_list()
        self._update_status()

    def _on_delete_box(self):
        if not self._current_image:
            return
        row = self.box_list.currentRow()
        if row < 0:
            return
        boxes = self._boxes_map.get(self._current_image.name, [])
        if 0 <= row < len(boxes):
            del boxes[row]
            self._dirty.add(self._current_image.name)
            self._refresh_box_list()
            self._update_status()

    def _on_clear_boxes(self):
        if not self._current_image:
            return
        if not self._boxes_map.get(self._current_image.name):
            return
        reply = QMessageBox.question(
            self, "确认", "确定清空当前图片的所有标注框吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._boxes_map[self._current_image.name] = []
        self._dirty.add(self._current_image.name)
        self._refresh_box_list()
        self._update_status()

    # ---------- 保存 ----------

    def _on_save_current(self):
        if not self._current_image:
            return
        self._save_one(self._current_image.name)
        self._dirty.discard(self._current_image.name)
        self.status_bar.showMessage(f"已保存: {self._current_image.name}")

    def _on_save_all(self):
        saved = 0
        for name in list(self._dirty):
            self._save_one(name)
            saved += 1
        self._dirty.clear()
        QMessageBox.information(self, "完成", f"已保存 {saved} 张图片的标注")
        self.accept()

    def _on_cancel(self):
        if self._dirty:
            reply = QMessageBox.question(
                self, "确认退出",
                f"有 {len(self._dirty)} 张图片的标注未保存，确认退出？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.reject()

    def _save_one(self, image_name):
        boxes = self._boxes_map.get(image_name, [])
        self.dataset_manager.save_label_for_image(image_name, boxes)

    # ---------- 辅助 ----------

    def _resolve_path(self, path_str):
        p = Path(path_str)
        return p if p.is_absolute() else self.project_root / p

    def _load_boxes_for_image(self, image_name):
        """从 registry 加载图片已有标注（按 stem 匹配 .txt）"""
        stem = Path(image_name).stem
        labels = self.dataset_manager.list_labels()
        for lbl in labels:
            if Path(lbl.name).stem == stem:
                # 读取 txt 文件
                path = self._resolve_path(lbl.path)
                if not path.exists():
                    return []
                boxes = []
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                cid = int(parts[0])
                                xc = float(parts[1])
                                yc = float(parts[2])
                                w = float(parts[3])
                                h = float(parts[4])
                                boxes.append((cid, xc, yc, w, h))
                except Exception:
                    return []
                return boxes
        return []

    def _update_status(self):
        if not self._current_image:
            self.status_bar.showMessage("无图片")
            return
        m = self._current_image
        boxes = self._boxes_map.get(m.name, [])
        row = self.image_list.currentRow() + 1
        total = self.image_list.count()
        dirty_mark = " *" if m.name in self._dirty else ""
        self.status_bar.showMessage(
            f"{m.name} | {len(boxes)} 框 | 第 {row}/{total} 张{dirty_mark}"
        )

    # ---------- 关闭事件 ----------

    def closeEvent(self, event):
        if self._dirty:
            reply = QMessageBox.question(
                self, "确认退出",
                f"有 {len(self._dirty)} 张图片的标注未保存，确认退出？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
