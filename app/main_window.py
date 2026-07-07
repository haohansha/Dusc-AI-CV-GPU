import sys
from pathlib import Path

import torch
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QAction, QStatusBar, QToolBar, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from app.models.app_config import AppConfig
from modules.model_manager import ModelManager
from modules.dataset_manager import DatasetManager
from modules.inference_engine import InferenceEngine
from modules.export_engine import ExportEngine


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._project_root = Path(__file__).parent.parent

        self._model_manager = ModelManager(self._project_root)
        self._dataset_manager = DatasetManager(self._project_root)
        self._inference_engine = InferenceEngine(self._project_root)
        self._export_engine = ExportEngine(self._project_root, app_config=self._config)

        self._model_manager.scan_models_dir()

        self.setWindowTitle("工业烟雾AI视觉识别与管理平台")
        self.setMinimumSize(1200, 1040)

        self._init_menu_bar()
        self._init_toolbar()
        self._init_status_bar()
        self._init_central_widget()
        self._check_environment()

        geometry_hex = self._config.get("window_geometry", "")
        if geometry_hex:
            self.restoreGeometry(bytes.fromhex(geometry_hex))

    def _init_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _open_settings(self):
        try:
            from app.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(self._config, self)
            if dialog.exec_():
                theme = self._config.get("theme", "light")
                if theme == "dark":
                    from PyQt5.QtWidgets import QApplication
                    QApplication.instance().setStyleSheet(
                        open(Path(__file__).parent / "resources" / "dark.qss", "r").read()
                    )
                else:
                    QApplication.instance().setStyleSheet("")
        except ImportError:
            QMessageBox.information(self, "提示", "设置功能即将推出")

    def _init_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)

        toolbar.addAction("导入模型").triggered.connect(lambda: self._tab_widget.setCurrentIndex(0))
        toolbar.addAction("导入素材").triggered.connect(lambda: self._tab_widget.setCurrentIndex(1))
        toolbar.addAction("开始训练").triggered.connect(lambda: self._tab_widget.setCurrentIndex(2))

    def _init_status_bar(self):
        statusbar = self.statusBar()

        self._gpu_status_label = QLabel("GPU: 检测中...")
        statusbar.addWidget(self._gpu_status_label)

        self._model_status_label = QLabel("模型: 未加载")
        statusbar.addPermanentWidget(self._model_status_label)

    def _init_central_widget(self):
        from app.ui.model_page import ModelPage
        from app.ui.data_page import DataPage
        from app.ui.train_page import TrainPage
        from app.ui.inference_page import InferencePage
        from app.ui.deploy_page import DeployPage

        self._tab_widget = QTabWidget()
        self.setCentralWidget(self._tab_widget)

        self.tab_model = ModelPage(self._project_root, self._model_manager)
        self._tab_widget.addTab(self.tab_model, "模型管理")

        self.tab_data = DataPage(self._project_root, self._dataset_manager)
        self._tab_widget.addTab(self.tab_data, "数据管理")

        self.tab_train = TrainPage(
            self._project_root, None,
            self._model_manager, self._dataset_manager
        )
        self._tab_widget.addTab(self.tab_train, "微调训练")

        self.tab_inference = InferencePage(
            self._project_root, self._inference_engine,
            self._model_manager, self._dataset_manager
        )
        self._tab_widget.addTab(self.tab_inference, "推理检测")

        self.tab_deploy = DeployPage(
            self._project_root, self._export_engine,
            self._model_manager, app_config=self._config
        )
        self._tab_widget.addTab(self.tab_deploy, "Jetson部署")

    def _check_environment(self):
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            self._gpu_status_label.setText(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
            self._model_status_label.setText("模型: 就绪")
        else:
            self._gpu_status_label.setText("GPU: 不可用 (CPU模式)")
            self._model_status_label.setText("模型: CPU模式")

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "工业烟雾AI视觉识别与管理平台 v1.0\n基于 YOLOv8 + PyTorch\n适用于 Jetson Nano/Orin 部署"
        )

    def closeEvent(self, event):
        geometry_hex = self.saveGeometry().toHex().data().decode()
        self._config.set("window_geometry", geometry_hex)
        super().closeEvent(event)
