# -*- coding: utf-8 -*-
"""
UI 排版重构 Demo —— 纯界面展示，无业务逻辑。
运行方式: python -m app.demo
"""
import sys
import os
from pathlib import Path

# 必须在 PyQt5 之前 import torch（DLL 加载修复）—— Demo 为纯UI，不依赖 torch
# 若后续接回业务模块，请在 main.py 中恢复 import torch

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout, QComboBox,
    QRadioButton, QButtonGroup, QSpinBox, QDoubleSpinBox, QSlider,
    QProgressBar, QTextEdit, QCheckBox, QAbstractItemView, QHeaderView,
    QMessageBox, QFrame, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush


# ============================================================
# 通用占位行为
# ============================================================
def _placeholder(parent, name):
    QMessageBox.information(parent, "Demo", f"{name} 功能将在审核通过后接入。")


# ============================================================
# 页面一：数据管理（三栏：素材列表 | 预览区 | 标签管理）
# ============================================================
class DataManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_data = [
            {"name": "factory.mp4", "type": "video"},
            {"name": "smoke_01.jpg", "type": "image", "labels": [
                {"cls": "smoke", "x": 0.12, "y": 0.23, "w": 0.45, "h": 0.67},
                {"cls": "smoke", "x": 0.50, "y": 0.10, "w": 0.30, "h": 0.40},
            ]},
            {"name": "smoke_02.jpg", "type": "image", "labels": [
                {"cls": "smoke", "x": 0.20, "y": 0.30, "w": 0.50, "h": 0.45},
            ]},
            {"name": "test.avi", "type": "video"},
        ]
        self._setup_ui()
        self._load_media_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部按钮栏（唯一一组）
        btn_row = QHBoxLayout()
        self.btn_import_video = QPushButton("导入视频")
        self.btn_import_image = QPushButton("导入图片")
        self.btn_delete = QPushButton("删除")
        self.btn_labelimg = QPushButton("启动LabelImg")
        for btn in (self.btn_import_video, self.btn_import_image,
                    self.btn_delete, self.btn_labelimg):
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 三栏 QSplitter 1:3:1
        splitter = QSplitter(Qt.Horizontal)

        # 左栏：素材列表
        left_group = QGroupBox("素材列表")
        left_layout = QVBoxLayout(left_group)
        self.media_list = QListWidget()
        self.media_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.media_list.currentRowChanged.connect(self._on_media_selected)
        left_layout.addWidget(self.media_list)
        splitter.addWidget(left_group)

        # 中栏：预览区
        mid_group = QGroupBox("预览区")
        mid_layout = QVBoxLayout(mid_group)
        self.preview_label = QLabel("请选择左侧素材进行预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(480, 360)
        self.preview_label.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #fafafa; color: #888888; }"
        )
        mid_layout.addWidget(self.preview_label)
        splitter.addWidget(mid_group)

        # 右栏：标签管理
        self.right_group = QGroupBox("标签管理")
        right_layout = QVBoxLayout(self.right_group)
        right_layout.addWidget(QLabel("当前图片标签"))

        self.label_list = QListWidget()
        self.label_list.setMaximumHeight(200)
        right_layout.addWidget(self.label_list)

        add_row = QHBoxLayout()
        self.btn_add_label = QPushButton("+ 添加标签")
        add_row.addWidget(self.btn_add_label)
        right_layout.addLayout(add_row)

        cls_row = QHBoxLayout()
        cls_row.addWidget(QLabel("类别:"))
        self.cls_combo = QComboBox()
        self.cls_combo.addItems(["smoke", "fire", "person"])
        cls_row.addWidget(self.cls_combo)
        cls_row.addStretch()
        right_layout.addLayout(cls_row)

        coord_form = QFormLayout()
        self.spin_x = QDoubleSpinBox()
        self.spin_y = QDoubleSpinBox()
        self.spin_w = QDoubleSpinBox()
        self.spin_h = QDoubleSpinBox()
        for spin in (self.spin_x, self.spin_y, self.spin_w, self.spin_h):
            spin.setRange(0.0, 1.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.01)
        self.spin_w.setValue(0.30)
        self.spin_h.setValue(0.40)
        coord_form.addRow("x:", self.spin_x)
        coord_form.addRow("y:", self.spin_y)
        coord_form.addRow("w:", self.spin_w)
        coord_form.addRow("h:", self.spin_h)
        right_layout.addLayout(coord_form)

        right_layout.addStretch()
        splitter.addWidget(self.right_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([200, 600, 200])
        layout.addWidget(splitter)

        # 底部状态
        self.status_label = QLabel("共 4 个素材 | 当前: 无选择")
        self.status_label.setStyleSheet("color: #555555; padding: 4px;")
        layout.addWidget(self.status_label)

        # 连接占位信号
        self.btn_import_video.clicked.connect(lambda: _placeholder(self, "导入视频"))
        self.btn_import_image.clicked.connect(lambda: _placeholder(self, "导入图片"))
        self.btn_delete.clicked.connect(lambda: _placeholder(self, "删除"))
        self.btn_labelimg.clicked.connect(lambda: _placeholder(self, "启动LabelImg"))
        self.btn_add_label.clicked.connect(lambda: _placeholder(self, "添加标签"))

    def _load_media_list(self):
        self.media_list.clear()
        for m in self._media_data:
            self.media_list.addItem(QListWidgetItem(m["name"]))

    def _on_media_selected(self, row):
        if row < 0 or row >= len(self._media_data):
            return
        info = self._media_data[row]
        name = info["name"]
        mtype = info["type"]

        # 预览区占位
        if mtype == "video":
            self.preview_label.setText(f"[视频预览]\n{name}\n(首帧)")
            self.right_group.setVisible(False)
            self.status_label.setText(f"共 {len(self._media_data)} 个素材 | 当前: {name} (视频，无标签)")
        else:
            labels = info.get("labels", [])
            self.preview_label.setText(f"[图片预览]\n{name}\n(含 {len(labels)} 个标注框)")
            self.right_group.setVisible(True)
            self._load_labels(labels)
            self.status_label.setText(f"共 {len(self._media_data)} 个素材 | 当前: {name} ({len(labels)}个标签)")

    def _load_labels(self, labels):
        self.label_list.clear()
        for i, lb in enumerate(labels):
            text = (f"#{i} {lb['cls']}   "
                    f"x:{lb['x']:.2f} y:{lb['y']:.2f} "
                    f"w:{lb['w']:.2f} h:{lb['h']:.2f}")
            self.label_list.addItem(QListWidgetItem(text))


# ============================================================
# 页面二：模型管理（上半模型列表+详情，下半可折叠微调训练）
# ============================================================
class ModelManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._models_data = [
            {"name": "yolov8n.pt", "type": "预训练", "classes": 80, "size": "6.2MB",
             "date": "2025-01-15", "status": "就绪",
             "path": "models/yolov8n.pt", "arch": "YOLOv8", "cls_names": "coco 80类",
             "mAP": "0.37"},
            {"name": "smoke_best.pt", "type": "微调", "classes": 1, "size": "6.1MB",
             "date": "2025-01-20", "status": "就绪",
             "path": "models/smoke_best.pt", "arch": "YOLOv8", "cls_names": "smoke",
             "mAP": "0.85"},
            {"name": "factory.pt", "type": "导入", "classes": 1, "size": "6.1MB",
             "date": "2025-01-22", "status": "就绪",
             "path": "models/factory.pt", "arch": "YOLOv8", "cls_names": "smoke",
             "mAP": "-"},
        ]
        self._setup_ui()
        self._load_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部按钮栏（唯一一组）
        btn_row = QHBoxLayout()
        self.btn_import = QPushButton("导入模型")
        self.btn_download = QPushButton("下载默认模型")
        self.btn_refresh = QPushButton("刷新")
        self.btn_compare = QPushButton("模型对比")
        for btn in (self.btn_import, self.btn_download, self.btn_refresh, self.btn_compare):
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 上下分割
        splitter = QSplitter(Qt.Vertical)

        # 上半区：模型列表 + 详情
        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)

        upper_layout.addWidget(QLabel("模型列表"))
        self.model_table = QTableWidget()
        self.model_table.setColumnCount(6)
        self.model_table.setHorizontalHeaderLabels(
            ["名称", "类型", "类别数", "大小", "创建时间", "状态"]
        )
        self.model_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.model_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model_table.itemSelectionChanged.connect(self._on_model_selected)
        upper_layout.addWidget(self.model_table)

        detail_group = QGroupBox("模型详情")
        detail_form = QFormLayout(detail_group)
        self.lbl_detail_path = QLabel("-")
        self.lbl_detail_arch = QLabel("-")
        self.lbl_detail_classes = QLabel("-")
        self.lbl_detail_mAP = QLabel("-")
        for lbl in (self.lbl_detail_path, self.lbl_detail_arch,
                    self.lbl_detail_classes, self.lbl_detail_mAP):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        detail_form.addRow("路径:", self.lbl_detail_path)
        detail_form.addRow("架构:", self.lbl_detail_arch)
        detail_form.addRow("类别列表:", self.lbl_detail_classes)
        detail_form.addRow("mAP:", self.lbl_detail_mAP)
        upper_layout.addWidget(detail_group)

        splitter.addWidget(upper)

        # 下半区：可折叠微调训练面板
        self.train_container = QWidget()
        train_outer = QVBoxLayout(self.train_container)
        train_outer.setContentsMargins(0, 0, 0, 0)

        # 折叠标题栏
        title_row = QHBoxLayout()
        self.btn_toggle_train = QPushButton("▼ 微调训练")
        self.btn_toggle_train.setFlat(True)
        self.btn_toggle_train.setStyleSheet(
            "QPushButton { text-align: left; font-weight: bold; padding: 6px; }"
        )
        self.btn_toggle_train.clicked.connect(self._toggle_train_panel)
        title_row.addWidget(self.btn_toggle_train)
        title_row.addStretch()
        train_outer.addLayout(title_row)

        # 训练面板内容
        self.train_panel = QWidget()
        train_layout = QVBoxLayout(self.train_panel)
        train_layout.setContentsMargins(8, 4, 8, 4)

        # 左右两列
        cols = QHBoxLayout()

        # 左列：数据源 + 基础模型
        left_col = QGroupBox("数据源")
        left_layout = QVBoxLayout(left_col)
        self.radio_default = QRadioButton("使用默认数据集")
        self.radio_imported = QRadioButton("使用导入素材")
        self.radio_default.setChecked(True)
        self.data_source_group = QButtonGroup(self)
        self.data_source_group.addButton(self.radio_default, 0)
        self.data_source_group.addButton(self.radio_imported, 1)
        left_layout.addWidget(self.radio_default)
        left_layout.addWidget(self.radio_imported)

        left_layout.addWidget(QLabel("基础模型:"))
        self.combo_base_model = QComboBox()
        self.combo_base_model.addItems(["yolov8n.pt", "smoke_best.pt", "factory.pt"])
        left_layout.addWidget(self.combo_base_model)
        left_layout.addStretch()
        cols.addWidget(left_col)

        # 右列：训练参数
        right_col = QGroupBox("训练参数")
        right_form = QFormLayout(right_col)
        self.spin_epochs = QSpinBox()
        self.spin_epochs.setRange(1, 500)
        self.spin_epochs.setValue(50)
        right_form.addRow("训练轮数:", self.spin_epochs)

        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 128)
        self.spin_batch.setValue(8)
        right_form.addRow("批次:", self.spin_batch)

        self.spin_lr = QDoubleSpinBox()
        self.spin_lr.setRange(0.00001, 0.1)
        self.spin_lr.setDecimals(5)
        self.spin_lr.setSingleStep(0.00001)
        self.spin_lr.setValue(0.0001)
        right_form.addRow("学习率:", self.spin_lr)

        self.spin_imgsz = QSpinBox()
        self.spin_imgsz.setRange(320, 1280)
        self.spin_imgsz.setSingleStep(32)
        self.spin_imgsz.setValue(640)
        right_form.addRow("尺寸:", self.spin_imgsz)

        self.btn_advanced = QPushButton("高级选项 ▼")
        self.btn_advanced.clicked.connect(self._toggle_advanced)
        right_form.addRow(self.btn_advanced)

        self.advanced_panel = QWidget()
        adv_form = QFormLayout(self.advanced_panel)
        self.combo_optimizer = QComboBox()
        self.combo_optimizer.addItems(["AdamW", "SGD", "Adam"])
        adv_form.addRow("优化器:", self.combo_optimizer)
        self.spin_warmup = QSpinBox()
        self.spin_warmup.setRange(0, 10)
        self.spin_warmup.setValue(2)
        adv_form.addRow("预热轮数:", self.spin_warmup)
        self.spin_patience = QSpinBox()
        self.spin_patience.setRange(1, 50)
        self.spin_patience.setValue(15)
        adv_form.addRow("早停耐心:", self.spin_patience)
        self.chk_cos_lr = QCheckBox("余弦学习率")
        self.chk_cos_lr.setChecked(True)
        adv_form.addRow("", self.chk_cos_lr)
        self.advanced_panel.setVisible(False)
        right_form.addRow(self.advanced_panel)

        cols.addWidget(right_col)
        train_layout.addLayout(cols)

        # 训练控制
        ctrl_row = QHBoxLayout()
        self.btn_start_train = QPushButton("开始训练")
        self.btn_start_train.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 20px; }"
        )
        self.btn_stop_train = QPushButton("停止训练")
        self.btn_stop_train.setEnabled(False)
        self.btn_stop_train.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 6px 20px; }"
        )
        ctrl_row.addWidget(self.btn_start_train)
        ctrl_row.addWidget(self.btn_stop_train)
        ctrl_row.addStretch()
        train_layout.addLayout(ctrl_row)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(60)
        self.progress_bar.setFormat("训练中... 30/50 (60%)")
        train_layout.addWidget(self.progress_bar)

        # 日志面板
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setFont(QFont("Courier New", 20))
        self.log_text.setHtml(
            '<span style="color:#000000;">[10:30:01] [INFO] 开始训练...</span><br>'
            '<span style="color:#000000;">[10:30:15] [INFO] Epoch 1/50 完成</span><br>'
            '<span style="color:#008000;">[10:30:30] [SUCCESS] 训练完成！mAP: 0.85</span>'
        )
        train_layout.addWidget(self.log_text)

        train_outer.addWidget(self.train_panel)
        splitter.addWidget(self.train_container)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)

        # 连接占位信号
        self.btn_import.clicked.connect(lambda: _placeholder(self, "导入模型"))
        self.btn_download.clicked.connect(lambda: _placeholder(self, "下载默认模型"))
        self.btn_refresh.clicked.connect(lambda: _placeholder(self, "刷新"))
        self.btn_compare.clicked.connect(lambda: _placeholder(self, "模型对比"))
        self.btn_start_train.clicked.connect(lambda: _placeholder(self, "开始训练"))
        self.btn_stop_train.clicked.connect(lambda: _placeholder(self, "停止训练"))

    def _load_models(self):
        self.model_table.setRowCount(len(self._models_data))
        for row, m in enumerate(self._models_data):
            self.model_table.setItem(row, 0, QTableWidgetItem(m["name"]))
            self.model_table.setItem(row, 1, QTableWidgetItem(m["type"]))
            self.model_table.setItem(row, 2, QTableWidgetItem(str(m["classes"])))
            self.model_table.setItem(row, 3, QTableWidgetItem(m["size"]))
            self.model_table.setItem(row, 4, QTableWidgetItem(m["date"]))
            self.model_table.setItem(row, 5, QTableWidgetItem(m["status"]))

    def _on_model_selected(self):
        rows = set(item.row() for item in self.model_table.selectedItems())
        if not rows:
            return
        row = min(rows)
        if row < len(self._models_data):
            m = self._models_data[row]
            self.lbl_detail_path.setText(m["path"])
            self.lbl_detail_arch.setText(m["arch"])
            self.lbl_detail_classes.setText(m["cls_names"])
            self.lbl_detail_mAP.setText(m["mAP"])

    def _toggle_train_panel(self):
        visible = self.train_panel.isVisible()
        self.train_panel.setVisible(not visible)
        self.btn_toggle_train.setText("▲ 微调训练" if not visible else "▼ 微调训练")

    def _toggle_advanced(self):
        visible = self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(not visible)
        self.btn_advanced.setText("高级选项 ▲" if not visible else "高级选项 ▼")


# ============================================================
# 页面三：推理检测（左配置 | 右预览+结果）
# ============================================================
class InferenceDemoPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        # 左栏：配置面板
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)

        model_group = QGroupBox("模型选择")
        model_layout = QVBoxLayout(model_group)
        self.combo_model = QComboBox()
        self.combo_model.addItems(["smoke_best.pt", "yolov8n.pt", "factory.pt"])
        model_layout.addWidget(self.combo_model)
        left_layout.addWidget(model_group)

        source_group = QGroupBox("输入源")
        source_layout = QVBoxLayout(source_group)
        self.radio_image = QRadioButton("图片")
        self.radio_video = QRadioButton("视频")
        self.radio_camera = QRadioButton("摄像头")
        self.radio_image.setChecked(True)
        self.source_group = QButtonGroup(self)
        self.source_group.addButton(self.radio_image, 0)
        self.source_group.addButton(self.radio_video, 1)
        self.source_group.addButton(self.radio_camera, 2)
        rb_row = QHBoxLayout()
        rb_row.addWidget(self.radio_image)
        rb_row.addWidget(self.radio_video)
        rb_row.addWidget(self.radio_camera)
        source_layout.addLayout(rb_row)

        self.combo_media = QComboBox()
        self.combo_media.addItems(["smoke_01.jpg", "smoke_02.jpg"])
        source_layout.addWidget(self.combo_media)

        browse_row = QHBoxLayout()
        self.btn_browse = QPushButton("浏览文件")
        browse_row.addWidget(self.btn_browse)
        browse_row.addStretch()
        source_layout.addLayout(browse_row)
        left_layout.addWidget(source_group)

        param_group = QGroupBox("参数")
        param_layout = QVBoxLayout(param_group)
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("置信度:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(25)
        self.conf_label = QLabel("0.25")
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v/100:.2f}")
        )
        conf_row.addWidget(self.conf_slider)
        conf_row.addWidget(self.conf_label)
        param_layout.addLayout(conf_row)
        left_layout.addWidget(param_group)

        ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout(ctrl_group)
        self.btn_start = QPushButton("开始检测")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 16px; }"
        )
        self.btn_stop = QPushButton("停止检测")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 6px 16px; }"
        )
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        left_layout.addWidget(ctrl_group)

        left_layout.addStretch()
        splitter.addWidget(left)

        # 右栏：预览 + 结果
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)

        preview_group = QGroupBox("检测画面")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("[检测画面预览区]\n选择模型和输入源后点击开始检测")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #fafafa; color: #888888; }"
        )
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_group, stretch=3)

        results_group = QGroupBox("检测结果")
        results_layout = QVBoxLayout(results_group)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(
            ["类别", "置信度", "位置(x1,y1,x2,y2)", "面积占比"]
        )
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 假数据
        self.results_table.setRowCount(2)
        self.results_table.setItem(0, 0, QTableWidgetItem("smoke"))
        self.results_table.setItem(0, 1, QTableWidgetItem("85.2%"))
        self.results_table.setItem(0, 2, QTableWidgetItem("(120, 80, 300, 280)"))
        self.results_table.setItem(0, 3, QTableWidgetItem("12.5%"))
        self.results_table.setItem(1, 0, QTableWidgetItem("smoke"))
        self.results_table.setItem(1, 1, QTableWidgetItem("72.1%"))
        self.results_table.setItem(1, 2, QTableWidgetItem("(400, 50, 550, 200)"))
        self.results_table.setItem(1, 3, QTableWidgetItem("8.3%"))
        results_layout.addWidget(self.results_table)
        self.stats_label = QLabel("总帧数: 1 | FPS: 45.2 | 检测数: 2")
        results_layout.addWidget(self.stats_label)
        right_layout.addWidget(results_group, stretch=2)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([300, 700])

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

        # 占位连接
        self.btn_browse.clicked.connect(lambda: _placeholder(self, "浏览文件"))
        self.btn_start.clicked.connect(lambda: _placeholder(self, "开始检测"))
        self.btn_stop.clicked.connect(lambda: _placeholder(self, "停止检测"))


# ============================================================
# 页面四：Jetson部署
# ============================================================
class DeployDemoPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部按钮栏
        btn_row = QHBoxLayout()
        self.btn_export_trt = QPushButton("导出 TensorRT")
        self.btn_export_onnx = QPushButton("导出 ONNX")
        self.btn_deploy_pkg = QPushButton("生成部署包")
        for btn in (self.btn_export_trt, self.btn_export_onnx, self.btn_deploy_pkg):
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 模型选择
        model_group = QGroupBox("选择模型")
        model_layout = QVBoxLayout(model_group)
        self.combo_model = QComboBox()
        self.combo_model.addItems(["smoke_best.pt", "yolov8n.pt", "factory.pt"])
        model_layout.addWidget(self.combo_model)
        layout.addWidget(model_group)

        # 高级选项（可折叠）
        adv_group = QGroupBox("高级选项")
        adv_layout = QVBoxLayout(adv_group)
        self.btn_toggle_adv = QPushButton("▼ 展开")
        self.btn_toggle_adv.clicked.connect(self._toggle_advanced)
        adv_layout.addWidget(self.btn_toggle_adv)

        self.adv_panel = QWidget()
        adv_form = QFormLayout(self.adv_panel)
        self.spin_imgsz = QSpinBox()
        self.spin_imgsz.setRange(320, 1280)
        self.spin_imgsz.setSingleStep(32)
        self.spin_imgsz.setValue(640)
        adv_form.addRow("输入分辨率:", self.spin_imgsz)
        self.combo_precision = QComboBox()
        self.combo_precision.addItems(["FP16", "INT8"])
        adv_form.addRow("精度:", self.combo_precision)
        self.spin_workspace = QSpinBox()
        self.spin_workspace.setRange(1, 16)
        self.spin_workspace.setValue(4)
        adv_form.addRow("Workspace (GB):", self.spin_workspace)
        self.adv_panel.setVisible(False)
        adv_layout.addWidget(self.adv_panel)
        layout.addWidget(adv_group)

        # 部署说明
        instr_group = QGroupBox("部署说明")
        instr_layout = QVBoxLayout(instr_group)
        self.instr_text = QTextEdit()
        self.instr_text.setReadOnly(True)
        self.instr_text.setMaximumHeight(200)
        self.instr_text.setPlainText(
            "=== Jetson Nano/Orin 部署步骤 ===\n"
            "1. 将部署包解压到 Jetson 设备\n"
            "2. 运行: bash setup_jetson.sh\n"
            "3. 测试: python3 smoke_detect.py --model xxx.engine\n"
            "4. 生产: python3 smoke_detect.py --model xxx.engine --rtsp rtsp://...\n"
            "\n"
            "=== 支持的模型格式 ===\n"
            "- TensorRT (.engine): 推理速度最快, Jetson 推荐\n"
            "- ONNX (.onnx): 跨平台兼容\n"
            "- PyTorch (.pt): 直接推理, 速度较慢\n"
            "\n"
            "=== 性能参考 (Jetson Orin Nano 8GB) ===\n"
            "- TensorRT FP16: ~60-80 FPS\n"
            "- ONNX Runtime: ~25-40 FPS\n"
            "- PyTorch: ~15-25 FPS"
        )
        instr_layout.addWidget(self.instr_text)
        layout.addWidget(instr_group)

        # 验证导出
        verify_group = QGroupBox("验证导出")
        verify_layout = QHBoxLayout(verify_group)
        self.btn_verify = QPushButton("验证导出")
        verify_layout.addWidget(self.btn_verify)
        self.lbl_verify = QLabel("TensorRT (.engine): ✓ 有效\nONNX (.onnx): ✓ 有效")
        self.lbl_verify.setStyleSheet("color: #008000; padding: 4px;")
        verify_layout.addWidget(self.lbl_verify)
        verify_layout.addStretch()
        layout.addWidget(verify_group)

        layout.addStretch()

        # 占位连接
        self.btn_export_trt.clicked.connect(lambda: _placeholder(self, "导出 TensorRT"))
        self.btn_export_onnx.clicked.connect(lambda: _placeholder(self, "导出 ONNX"))
        self.btn_deploy_pkg.clicked.connect(lambda: _placeholder(self, "生成部署包"))
        self.btn_verify.clicked.connect(lambda: _placeholder(self, "验证导出"))

    def _toggle_advanced(self):
        visible = self.adv_panel.isVisible()
        self.adv_panel.setVisible(not visible)
        self.btn_toggle_adv.setText("▲ 收起" if not visible else "▼ 展开")


# ============================================================
# 主窗口（菜单栏 + 状态栏 + 4 tab，无工具栏）
# ============================================================
class DemoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("工业烟雾AI视觉识别与管理平台 — UI Demo")
        self.setMinimumSize(1200, 800)

        self._init_menu_bar()
        self._init_status_bar()
        self._init_tabs()

    def _init_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        settings_action = file_menu.addAction("设置")
        settings_action.triggered.connect(lambda: _placeholder(self, "设置"))
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self._show_about)

    def _init_status_bar(self):
        statusbar = self.statusBar()
        self.gpu_label = QLabel("GPU: NVIDIA RTX 3060 (12.0 GB)")
        statusbar.addWidget(self.gpu_label)
        self.model_label = QLabel("模型: smoke_best.pt 已加载")
        statusbar.addPermanentWidget(self.model_label)

    def _init_tabs(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # 顺序：数据管理 → 模型管理 → 推理检测 → Jetson部署
        self.tab_data = DataManagementPage()
        self.tab_widget.addTab(self.tab_data, "数据管理")

        self.tab_model = ModelManagementPage()
        self.tab_widget.addTab(self.tab_model, "模型管理")

        self.tab_inference = InferenceDemoPage()
        self.tab_widget.addTab(self.tab_inference, "推理检测")

        self.tab_deploy = DeployDemoPage()
        self.tab_widget.addTab(self.tab_deploy, "Jetson部署")

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "工业烟雾AI视觉识别与管理平台 v1.0\n"
            "UI 排版重构 Demo\n\n"
            "基于 YOLOv8 + PyTorch\n"
            "适用于 Jetson Nano/Orin 部署\n\n"
            "本 Demo 仅展示界面排版，功能将在审核通过后接入。"
        )


# ============================================================
# 入口
# ============================================================
def main():
    project_root = Path(__file__).parent.parent
    os.environ.setdefault("YOLO_CONFIG_DIR", str(project_root / ".ultralytics"))
    os.makedirs(str(project_root / ".ultralytics" / "Ultralytics"), exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("工业烟雾AI视觉识别与管理平台 - Demo")

    # 加载白色主题
    qss_path = project_root / "app" / "resources" / "light.qss"
    if qss_path.exists():
        app.setStyleSheet(open(qss_path, "r", encoding="utf-8").read())

    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
