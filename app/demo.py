# -*- coding: utf-8 -*-
"""
UI 排版重构 Demo —— 纯界面展示，无业务逻辑。
运行方式: python -m app.demo
"""
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

# 必须在 PyQt5 之前 import torch（DLL 加载修复）—— Demo 为纯UI，不依赖 torch
# 若后续接回业务模块，请在 main.py 中恢复 import torch

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout, QComboBox,
    QRadioButton, QButtonGroup, QSlider,
    QMessageBox, QAbstractItemView, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush


# ============================================================
# 通用占位行为
# ============================================================
def _placeholder(parent, name):
    QMessageBox.information(parent, "Demo", f"{name} 功能将在审核通过后接入。")


# ============================================================
# 页面一：数据管理（使用真实 DataPage，接入 DatasetManager 后端）
# ============================================================
class DataManagementPage(QWidget):
    """Demo 包装器：用真实 DataPage + 真实 DatasetManager 展示完整数据导入功能"""
    def __init__(self, parent=None):
        super().__init__(parent)
        from app.ui.data_page import DataPage
        from modules.dataset_manager import DatasetManager

        project_root = Path(__file__).parent.parent
        dataset_mgr = DatasetManager(project_root)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._page = DataPage(project_root, dataset_mgr)
        layout.addWidget(self._page)


# ============================================================
# 页面二：模型管理（使用真实 ModelPage，Demo 用 mock ModelManager 避免 torch 依赖）
# ============================================================
class _MockModelInfo:
    """Demo 用轻量 ModelInfo，不依赖 ultralytics / torch"""
    def __init__(self, name, path, model_type, num_classes, class_names=None,
                 file_size=0, created_at="", status="ready", metrics=None):
        self.name = name
        self.path = path
        self.model_type = model_type
        self.num_classes = num_classes
        self.class_names = class_names or []
        self.file_size = file_size
        self.created_at = created_at
        self.status = status
        self.metrics = metrics or {}


class _DemoModelManager:
    """Demo 用 mock 模型管理器，提供真实 ModelPage 所需的接口"""
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        models_dir = self.project_root / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        self._models = []

    def list_models(self):
        return self._models

    def scan_models_dir(self):
        """扫描 models/ 目录，注册 .pt 文件"""
        models_dir = self.project_root / "models"
        self._models.clear()
        if models_dir.exists():
            for pt_file in sorted(models_dir.glob("*.pt")):
                stat = pt_file.stat()
                self._models.append(_MockModelInfo(
                    name=pt_file.name,
                    path=str(pt_file),
                    model_type="imported",
                    num_classes=0,
                    file_size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
                    status="ready",
                ))

    def import_model(self, file_path: Path):
        """复制模型文件到 models/ 目录"""
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        dest = self.project_root / "models" / file_path.name
        if dest.exists() and dest.samefile(file_path):
            self.scan_models_dir()
            for m in self._models:
                if m.name == file_path.name:
                    return m
            return None
        shutil.copy2(str(file_path), str(dest))
        self.scan_models_dir()
        for m in self._models:
            if m.name == file_path.name:
                return m
        return None

    def remove_model(self, name: str):
        """删除模型文件"""
        model_path = self.project_root / "models" / name
        if model_path.exists():
            model_path.unlink()
            self.scan_models_dir()
            return True
        return False


class ModelManagementPage(QWidget):
    """Demo 包装器：用真实 ModelPage + mock ModelManager + 真实 DatasetManager"""
    def __init__(self, parent=None):
        super().__init__(parent)
        from app.ui.model_page import ModelPage
        from modules.dataset_manager import DatasetManager

        project_root = Path(__file__).parent.parent
        model_mgr = _DemoModelManager(project_root)
        model_mgr.scan_models_dir()
        dataset_mgr = DatasetManager(project_root)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._page = ModelPage(project_root, model_mgr, dataset_mgr)
        layout.addWidget(self._page)


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
# 页面四：Jetson部署（使用真实 DeployPage，卡片式布局 + 深绿色主题）
# ============================================================
class DeployDemoPage(QWidget):
    """Demo 包装器：用真实 DeployPage + mock 依赖展示美化后的部署界面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        from app.ui.deploy_page import DeployPage

        # 构造 mock 依赖（Demo 模式不执行真实导出）
        project_root = Path(__file__).parent.parent
        mock_export = _MockExportEngine(project_root)
        mock_model_mgr = _MockModelManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._page = DeployPage(project_root, mock_export, mock_model_mgr, app_config=None)
        layout.addWidget(self._page)


class _MockModelManager:
    """Demo 用 mock 模型管理器"""
    def list_models(self):
        from collections import namedtuple
        Info = namedtuple("Info", ["name", "path"])
        return [
            Info("smoke_best.pt", "models/smoke_best.pt"),
            Info("yolov8n.pt", "models/yolov8n.pt"),
            Info("factory.pt", "models/factory.pt"),
        ]


class _MockExportEngine:
    """Demo 用 mock 导出引擎，所有操作返回占位结果"""
    def __init__(self, project_root):
        self.project_root = project_root

    def export_tensorrt(self, model_path, config=None, progress_callback=None):
        QMessageBox.information(None, "Demo", f"导出 TensorRT（Demo 占位）\n模型: {model_path}")
        return None

    def export_onnx(self, model_path, config=None, progress_callback=None):
        QMessageBox.information(None, "Demo", f"导出 ONNX（Demo 占位）\n模型: {model_path}")
        return None

    def generate_deploy_package(self, model_path, output_dir, progress_callback=None):
        QMessageBox.information(None, "Demo", f"生成部署包（Demo 占位）\n模型: {model_path}")
        return None

    def verify_export(self, output_path):
        # Demo 模式下模拟 ONNX 有效
        return output_path.endswith(".onnx")


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
