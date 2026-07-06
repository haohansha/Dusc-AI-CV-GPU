"""标签标注窗口：内置 labelImg 风格的 YOLO 标注编辑器"""

from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QPoint, QSize, QEvent
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QBrush, QKeySequence
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QListWidget, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QGroupBox, QFormLayout, QComboBox, QDoubleSpinBox, QMessageBox,
    QScrollArea, QSizePolicy, QFrame, QStatusBar, QInputDialog, QShortcut
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
        # Q键快速标注模式开关
        self._quick_mode = False
        # 拉框完成回调（由 dialog 设置）
        self._on_box_drawn_cb = None
        self._on_box_clicked_cb = None
        self._on_clear_selection_cb = None
        self._on_box_updated_cb = None
        # 拖动 / 调整大小状态
        self._drag_mode = None          # None | 'move' | 'resize'
        self._drag_start_pos = None     # 鼠标按下时的画布坐标
        self._drag_start_box = None     # 鼠标按下时框的归一化参数 (cid, xc, yc, w, h)
        # 右下角 handle 大小（像素）
        self._handle_size = 10

        self.setMouseTracking(True)
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("QWidget { border: 1px solid #cccccc; }")
        # 让画布可获取焦点，以便接收 Q 键
        self.setFocusPolicy(Qt.StrongFocus)

    def set_class_names(self, names):
        self._class_names = names

    def set_on_box_drawn(self, callback):
        """设置拉框完成回调（由 dialog 调用）"""
        self._on_box_drawn_cb = callback

    def set_on_box_clicked(self, callback):
        """设置点击已有框的回调（由 dialog 设置）"""
        self._on_box_clicked_cb = callback

    def set_on_clear_selection(self, callback):
        """设置点击空白处取消选中的回调（由 dialog 设置）"""
        self._on_clear_selection_cb = callback

    def set_on_box_updated(self, callback):
        """设置标注框被拖动/调整大小后的回调（由 dialog 设置）"""
        self._on_box_updated_cb = callback

    def _hit_test(self, pos):
        """检测点击位置
        返回 (idx, hit_type):
            hit_type='handle' → 点中选中框的右下角 handle
            hit_type='body'   → 点中某个框的内部
            hit_type='none'   → 空白
        """
        if not self._pixmap:
            return -1, 'none'
        offset = self._image_offset()
        img_w = self._pixmap.width()
        img_h = self._pixmap.height()
        # 优先：选中框的右下角 handle
        if 0 <= self._selected_index < len(self._boxes):
            cid, xc, yc, w, h = self._boxes[self._selected_index]
            cx = offset.x() + xc * img_w * self._scale
            cy = offset.y() + yc * img_h * self._scale
            bw = w * img_w * self._scale
            bh = h * img_h * self._scale
            rect = QRect(int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh))
            hs = self._handle_size
            handle_rect = QRect(rect.right() - hs, rect.bottom() - hs, hs * 2, hs * 2)
            if handle_rect.contains(pos):
                return self._selected_index, 'handle'
        # 然后：任意框内部
        for idx, (cid, xc, yc, w, h) in enumerate(self._boxes):
            cx = offset.x() + xc * img_w * self._scale
            cy = offset.y() + yc * img_h * self._scale
            bw = w * img_w * self._scale
            bh = h * img_h * self._scale
            rect = QRect(int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh))
            if rect.contains(pos):
                return idx, 'body'
        return -1, 'none'

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
            # 选中框：右下角绘制 handle（用于调整大小）
            if idx == self._selected_index:
                hs = self._handle_size
                handle_rect = QRect(rect.right() - hs, rect.bottom() - hs, hs * 2, hs * 2)
                painter.setBrush(QBrush(QColor(0, 120, 255)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawRect(handle_rect)
                painter.setBrush(Qt.NoBrush)

        # 画当前正在拉的框
        if self._drawing and self._start_point and self._end_point:
            pen = QPen(QColor(0, 200, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            r = QRect(self._start_point, self._end_point).normalized()
            painter.drawRect(r)

        # 快速模式开启时画绿色边框
        if self._quick_mode:
            pen = QPen(QColor(0, 180, 0), 3)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    # ---------- 鼠标事件 ----------

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self._pixmap:
            return
        idx, hit_type = self._hit_test(event.pos())
        # 1) 点中选中框的右下角 handle → 开始调整大小
        if hit_type == 'handle' and idx == self._selected_index:
            self._drag_mode = 'resize'
            self._drag_start_pos = event.pos()
            self._drag_start_box = self._boxes[idx]
            return
        # 2) 点中某个框内部
        if idx >= 0:
            # 通知 dialog 选中该框
            if self._on_box_clicked_cb:
                self._on_box_clicked_cb(idx)
            # 如果点中的就是当前已选中框，则立即开始拖动
            if idx == self._selected_index:
                self._drag_mode = 'move'
                self._drag_start_pos = event.pos()
                self._drag_start_box = self._boxes[idx]
            return
        # 3) 空白 → 取消选中
        if self._on_clear_selection_cb:
            self._on_clear_selection_cb()
        # 只有快速模式才继续画新框
        if not self._quick_mode:
            return
        self._drawing = True
        self._start_point = event.pos()
        self._end_point = event.pos()

    def mouseMoveEvent(self, event):
        # 拖动模式：移动选中框
        if self._drag_mode == 'move' and 0 <= self._selected_index < len(self._boxes):
            offset = self._image_offset()
            img_w = self._pixmap.width()
            img_h = self._pixmap.height()
            scale_w = max(img_w * self._scale, 1e-9)
            scale_h = max(img_h * self._scale, 1e-9)
            dx = (event.pos().x() - self._drag_start_pos.x()) / scale_w
            dy = (event.pos().y() - self._drag_start_pos.y()) / scale_h
            cid, xc0, yc0, w, h = self._drag_start_box
            xc = max(0.0, min(1.0, xc0 + dx))
            yc = max(0.0, min(1.0, yc0 + dy))
            self._boxes[self._selected_index] = (cid, xc, yc, w, h)
            self.update()
            if self._on_box_updated_cb:
                self._on_box_updated_cb(self._selected_index)
            return
        # 拖动模式：调整大小（保持中心点不变，改 w/h）
        if self._drag_mode == 'resize' and 0 <= self._selected_index < len(self._boxes):
            offset = self._image_offset()
            img_w = self._pixmap.width()
            img_h = self._pixmap.height()
            cid, xc0, yc0, w0, h0 = self._drag_start_box
            # 中心点在画布上的像素坐标
            cx_canvas = offset.x() + xc0 * img_w * self._scale
            cy_canvas = offset.y() + yc0 * img_h * self._scale
            # 新右下角 → 新宽高（中心不变，所以宽 = 2 * (right - cx)）
            new_w_canvas = max(8.0, (event.pos().x() - cx_canvas) * 2)
            new_h_canvas = max(8.0, (event.pos().y() - cy_canvas) * 2)
            new_w = new_w_canvas / max(img_w * self._scale, 1e-9)
            new_h = new_h_canvas / max(img_h * self._scale, 1e-9)
            new_w = max(0.01, min(1.0, new_w))
            new_h = max(0.01, min(1.0, new_h))
            self._boxes[self._selected_index] = (cid, xc0, yc0, new_w, new_h)
            self.update()
            if self._on_box_updated_cb:
                self._on_box_updated_cb(self._selected_index)
            return
        # 快速模式画框
        if not self._quick_mode or not self._drawing:
            return
        self._end_point = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        # 结束拖动 / 调整大小
        if self._drag_mode is not None:
            self._drag_mode = None
            self._drag_start_pos = None
            self._drag_start_box = None
            return
        if not self._quick_mode:
            return
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
        if self._on_box_drawn_cb:
            self._on_box_drawn_cb(xc, yc, w, h)


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
        self._setup_shortcut()
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

        # 左下角提示
        self.hint_label = QLabel("使用 Q 键和鼠标进行快速标注")
        self.hint_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
        self.hint_label.setWordWrap(True)
        left_layout.addWidget(self.hint_label)

        splitter.addWidget(left_group)

        # === 中栏：画布 + 手动输入 ===
        mid_group = QGroupBox("画布")
        mid_layout = QVBoxLayout(mid_group)

        self.canvas = AnnotationCanvas(self)
        self.canvas.set_class_names(self._class_names)
        # 设置拉框完成回调（不能用 parent()，因为画布被 QScrollArea 包裹）
        self.canvas.set_on_box_drawn(self._on_box_drawn)
        self.canvas.set_on_box_clicked(self._on_box_clicked)
        self.canvas.set_on_clear_selection(self._on_clear_selection)
        self.canvas.set_on_box_updated(self._on_box_updated)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.canvas)
        scroll.setMinimumHeight(420)
        # 快速模式下不响应拖动滚动，避免吞掉画布鼠标事件
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        mid_layout.addWidget(scroll, 1)

        # 标签详细参数区
        manual_group = QGroupBox("标签详细参数（YOLO 归一化坐标 0~1，xc/yc=中心点, w/h=宽高）")
        manual_form = QFormLayout(manual_group)
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

        self.btn_del_class = QPushButton("-")
        self.btn_del_class.setFixedWidth(28)
        self.btn_del_class.setToolTip("删除当前类别")
        self.btn_del_class.clicked.connect(self._on_del_class)
        class_row.addWidget(self.btn_del_class)
        manual_form.addRow("类别:", class_row)

        coord_row1 = QHBoxLayout()
        self.spin_xc = self._make_coord_spin()
        self.spin_yc = self._make_coord_spin()
        coord_row1.addWidget(QLabel("xc:"))
        coord_row1.addWidget(self.spin_xc)
        coord_row1.addWidget(QLabel("yc:"))
        coord_row1.addWidget(self.spin_yc)
        manual_form.addRow(coord_row1)

        coord_row2 = QHBoxLayout()
        self.spin_w = self._make_coord_spin()
        self.spin_h = self._make_coord_spin()
        coord_row2.addWidget(QLabel("w:"))
        coord_row2.addWidget(self.spin_w)
        coord_row2.addWidget(QLabel("h:"))
        coord_row2.addWidget(self.spin_h)
        manual_form.addRow(coord_row2)

        self.btn_add_manual = QPushButton("手动添加")
        self.btn_add_manual.clicked.connect(self._on_add_manual)
        self.btn_modify = QPushButton("修改")
        self.btn_modify.setToolTip("更新当前选中的标注框参数")
        self.btn_modify.clicked.connect(self._on_modify_box)
        self.btn_modify.setEnabled(False)  # 初始灰色禁用
        btn_row_manual = QHBoxLayout()
        btn_row_manual.addWidget(self.btn_add_manual)
        btn_row_manual.addWidget(self.btn_modify)
        manual_form.addRow(btn_row_manual)

        mid_layout.addWidget(manual_group)
        splitter.addWidget(mid_group)

        # === 右栏：标注框列表 ===
        right_group = QGroupBox("标注框")
        right_layout = QVBoxLayout(right_group)
        self.box_list = QListWidget()
        self.box_list.setSelectionMode(QListWidget.SingleSelection)
        self.box_list.currentRowChanged.connect(self._on_box_selected)
        # 安装事件过滤器：点击列表空白处取消选中
        self.box_list.installEventFilter(self)
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

    # ---------- 事件过滤器：点击列表空白处取消选中 ----------

    def eventFilter(self, obj, event):
        """监听 box_list 鼠标点击，点击空白处取消选中"""
        if obj is self.box_list and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                # 检查点击位置是否在某个 item 上
                item = self.box_list.itemAt(event.pos())
                if item is None:
                    # 点击空白处，取消选中
                    self.box_list.setCurrentRow(-1)
                    return True  # 消费事件，阻止默认行为
        return super().eventFilter(obj, event)

    # ---------- Q键快速标注模式 ----------

    def _make_coord_spin(self):
        """构造坐标输入框：0~1 归一化值，步长 0.05，可手动整段输入"""
        s = QDoubleSpinBox()
        s.setRange(0.0, 1.0)
        s.setSingleStep(0.05)
        s.setDecimals(3)
        s.setValue(0.5)
        # 允许直接输入完整数字（QDoubleSpinBox 默认会替换全选内容）
        s.setKeyboardTracking(True)
        return s

    def _setup_shortcut(self):
        """用 QShortcut 全局监听 Q 键，避免被子控件（QListWidget 搜索）消费"""
        self.shortcut_q = QShortcut(QKeySequence(Qt.Key_Q), self)
        # ApplicationShortcut 确保无论哪个子控件聚焦都能触发
        self.shortcut_q.setContext(Qt.ApplicationShortcut)
        self.shortcut_q.activated.connect(self._toggle_quick_mode)

    def _toggle_quick_mode(self):
        new_state = not self.canvas._quick_mode
        self.canvas.set_quick_mode(new_state)
        if new_state:
            cls = self.combo_class.currentText()
            self.status_bar.showMessage(f"快速标注模式: 开启 | 类别: {cls}")
            # 让画布获取焦点，确保鼠标事件被画布接收
            self.canvas.setFocus()
        else:
            self.status_bar.showMessage("快速标注模式: 关闭")
        self._update_quick_hint()

    def _update_quick_hint(self):
        """更新左下角提示文字"""
        if self.canvas._quick_mode:
            self.hint_label.setText("● 快速标注模式: 开启（按 Q 退出）| 类别: " + self.combo_class.currentText())
            self.hint_label.setStyleSheet("QLabel { color: #2a7d2a; font-weight: bold; font-size: 11px; }")
        else:
            self.hint_label.setText("使用 Q 键和鼠标进行快速标注")
            self.hint_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")

    # ---------- 类别管理 ----------

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

    def _on_del_class(self):
        """删除当前选中的类别（若被已有标签使用则拒绝）"""
        if len(self._class_names) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留 1 个类别")
            return
        idx = self.combo_class.currentIndex()
        name = self._class_names[idx]
        # 检查是否有标签使用该 class_id
        used_in = []
        for img_name, boxes in self._boxes_map.items():
            for cid, *_ in boxes:
                if cid == idx:
                    used_in.append(img_name)
                    break
        if used_in:
            QMessageBox.warning(
                self, "无法删除",
                f"类别 '{name}' 已被 {len(used_in)} 张图片的标注使用，无法删除。\n"
                f"请先清空或修改这些标注后再删除类别。"
            )
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除类别 '{name}' 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        # 删除类别
        del self._class_names[idx]
        self.combo_class.removeItem(idx)
        # 同步画布
        self.canvas.set_class_names(self._class_names)
        # 持久化
        self._save_class_names()
        self.status_bar.showMessage(f"已删除类别: {name}")

    def _on_class_changed(self):
        """类别下拉切换时：仅更新状态栏和提示（不自动改选中框，需点"修改"）"""
        self._update_quick_hint()
        if self.canvas._quick_mode:
            cls = self.combo_class.currentText()
            self.status_bar.showMessage(f"快速标注模式: 开启 | 类别: {cls}")

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
        # 取消选中 → 触发按钮互斥（"添加"亮起，"修改"灰色）
        self.box_list.setCurrentRow(-1)
        # 设置默认"添加"参数：
        #   有标签 → 与第一个标签一致
        #   无标签 → smoke + xc/yc/w/h=0.5
        if boxes:
            cid, xc, yc, w, h = boxes[0]
            if 0 <= cid < len(self._class_names):
                self.combo_class.blockSignals(True)
                self.combo_class.setCurrentIndex(cid)
                self.combo_class.blockSignals(False)
            self.spin_xc.setValue(xc)
            self.spin_yc.setValue(yc)
            self.spin_w.setValue(w)
            self.spin_h.setValue(h)
        else:
            if self._class_names:
                self.combo_class.blockSignals(True)
                self.combo_class.setCurrentIndex(0)
                self.combo_class.blockSignals(False)
            self.spin_xc.setValue(0.5)
            self.spin_yc.setValue(0.5)
            self.spin_w.setValue(0.5)
            self.spin_h.setValue(0.5)

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
        """选中右栏标注框时，同步类别下拉框、坐标输入框，并联动按钮启用状态"""
        self.canvas.set_selected(row)
        # 联动按钮：选中时"修改"亮起"添加"灰色；未选中时反过来
        selected = row >= 0
        self.btn_modify.setEnabled(selected)
        self.btn_add_manual.setEnabled(not selected)
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

    def _on_box_clicked(self, idx):
        """画布点击已有框时，同步选中右栏列表"""
        self.box_list.setCurrentRow(idx)

    def _on_clear_selection(self):
        """画布点击空白处时，取消选中右栏列表"""
        self.box_list.setCurrentRow(-1)

    def _on_box_updated(self, idx):
        """画布上拖动/调整大小过程中，同步数据到 _boxes_map 并刷新输入区"""
        if not self._current_image:
            return
        boxes = self._boxes_map.get(self._current_image.name, [])
        if idx < 0 or idx >= len(boxes):
            return
        # 从画布读取最新的框参数
        canvas_boxes = self.canvas.get_boxes()
        if idx >= len(canvas_boxes):
            return
        cid, xc, yc, w, h = canvas_boxes[idx]
        boxes[idx] = (cid, xc, yc, w, h)
        self._dirty.add(self._current_image.name)
        # 同步输入区（用户拖动时能看到参数实时变化）
        if 0 <= cid < len(self._class_names):
            self.combo_class.blockSignals(True)
            self.combo_class.setCurrentIndex(cid)
            self.combo_class.blockSignals(False)
        self.spin_xc.setValue(xc)
        self.spin_yc.setValue(yc)
        self.spin_w.setValue(w)
        self.spin_h.setValue(h)
        # 只更新当前行的文字（不 clear 整个列表，避免 currentRowChanged 循环和性能问题）
        if 0 <= idx < self.box_list.count():
            name = self._class_names[cid] if 0 <= cid < len(self._class_names) else str(cid)
            text = f"{name}  xc={xc:.3f} yc={yc:.3f} w={w:.3f} h={h:.3f}"
            item = self.box_list.item(idx)
            if item:
                item.setText(text)
        self._update_status()

    def _on_box_drawn(self, xc, yc, w, h):
        """AnnotationCanvas 拉框完成时回调"""
        if not self._current_image:
            return
        cid = self.combo_class.currentIndex()
        boxes = self._boxes_map.setdefault(self._current_image.name, [])
        boxes.append((cid, xc, yc, w, h))
        self._dirty.add(self._current_image.name)
        self._refresh_box_list()
        # 自动选中新画的标签，方便用户立即修改
        new_idx = len(boxes) - 1
        self.box_list.setCurrentRow(new_idx)
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
