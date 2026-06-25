from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QLabel, QFileDialog, QMessageBox, QInputDialog, QFormLayout)
from PyQt5.QtCore import Qt
from app.widgets.model_list import ModelListWidget
from app.models.app_config import AppConfig


def _fmt_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "-"
    size_bytes = float(size_bytes)
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / 1024:.1f} KB"


class ModelPage(QWidget):
    def __init__(self, project_root: Path, model_manager):
        super().__init__()
        self._project_root = Path(project_root)
        self._model_manager = model_manager
        self._app_config = AppConfig(project_root)
        self._setup_ui()
        self._connect_signals()
        self._refresh_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar_layout = QHBoxLayout()

        self._import_btn = QPushButton("导入模型")
        toolbar_layout.addWidget(self._import_btn)

        self._download_btn = QPushButton("下载默认模型")
        toolbar_layout.addWidget(self._download_btn)

        self._refresh_btn = QPushButton("刷新列表")
        toolbar_layout.addWidget(self._refresh_btn)

        self._compare_btn = QPushButton("模型对比")
        toolbar_layout.addWidget(self._compare_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        self._model_list_widget = ModelListWidget()
        layout.addWidget(self._model_list_widget)

        self._detail_group = QGroupBox("模型详情")
        detail_layout = QFormLayout()

        self._detail_path = QLabel("-")
        self._detail_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._detail_arch = QLabel("-")
        self._detail_classes = QLabel("-")
        self._detail_classes.setWordWrap(True)
        self._detail_mAP = QLabel("-")

        detail_layout.addRow("路径:", self._detail_path)
        detail_layout.addRow("架构:", self._detail_arch)
        detail_layout.addRow("类别列表:", self._detail_classes)
        detail_layout.addRow("mAP:", self._detail_mAP)

        self._detail_group.setLayout(detail_layout)
        layout.addWidget(self._detail_group)

    def _connect_signals(self):
        self._import_btn.clicked.connect(self._on_import)
        self._download_btn.clicked.connect(self._on_download)
        self._refresh_btn.clicked.connect(self._on_refresh)
        self._compare_btn.clicked.connect(self._on_compare)

        self._model_list_widget.model_selected.connect(self._on_model_selected)
        self._model_list_widget.model_double_clicked.connect(self._on_model_double_clicked)
        self._model_list_widget.import_clicked.connect(self._on_import)
        self._model_list_widget.download_clicked.connect(self._on_download)
        self._model_list_widget.refresh_clicked.connect(self._on_refresh)
        self._model_list_widget.compare_clicked.connect(self._on_compare_selected)
        self._model_list_widget.delete_requested.connect(self._on_delete)
        self._model_list_widget.set_default_requested.connect(self._on_set_default)

    def _refresh_models(self):
        try:
            models = self._model_manager.list_models()
            models_data = []
            for m in models:
                models_data.append({
                    "name": m.name,
                    "path": m.path,
                    "model_type": m.model_type,
                    "num_classes": m.num_classes,
                    "class_names": m.class_names,
                    "file_size": m.file_size,
                    "created_at": m.created_at,
                    "status": m.status,
                    "metrics": m.metrics,
                })
            self._model_list_widget.load_models(models_data)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新模型列表失败: {e}")

    def _show_model_detail(self, info):
        self._detail_path.setText(str(info.get("path", "-")))
        self._detail_arch.setText(str(info.get("model_type", "-")))
        class_names = info.get("class_names", [])
        if class_names:
            self._detail_classes.setText(", ".join(str(c) for c in class_names))
        else:
            num_classes = info.get("num_classes", 0)
            self._detail_classes.setText(f"{num_classes} 个类别")
        self._detail_mAP.setText(
            str(info.get("metrics", {}).get("mAP", "-"))
        )

    def _on_model_selected(self, info):
        self._show_model_detail(info)

    def _on_model_double_clicked(self, info):
        detail_text = (
            f"名称: {info.get('name', '-')}\n"
            f"路径: {info.get('path', '-')}\n"
            f"类型: {info.get('model_type', '-')}\n"
            f"大小: {_fmt_size(info.get('file_size'))}\n"
            f"类别数: {info.get('num_classes', '-')}\n"
            f"创建时间: {info.get('created_at', '-')}\n"
            f"状态: {info.get('status', '-')}\n"
            f"mAP: {info.get('metrics', {}).get('mAP', '-')}"
        )
        QMessageBox.information(self, "模型详情", detail_text)

    def _on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入模型",
            str(self._model_manager.project_root),
            "PyTorch 模型文件 (*.pt)"
        )
        if not file_path:
            return
        try:
            result = self._model_manager.import_model(Path(file_path))
            if result is None:
                QMessageBox.warning(self, "导入失败", f"无法导入模型文件: {file_path}")
                return
            QMessageBox.information(self, "导入成功", f"模型已导入: {result.name}")
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入模型时发生错误: {e}")

    def _on_download(self):
        sizes = ["n", "s", "m", "l", "x"]
        size, ok = QInputDialog.getItem(
            self, "选择模型大小",
            "请选择 YOLOv8 模型大小:",
            sizes, 0, False
        )
        if not ok:
            return
        try:
            QMessageBox.information(self, "下载中", "正在下载模型，请稍候...")
            result = self._model_manager.download_yolo(size)
            if result is None:
                QMessageBox.warning(self, "下载失败", "模型下载失败，请检查网络连接")
                return
            QMessageBox.information(
                self, "下载成功",
                f"已下载并加载模型: {result.name}\n路径: {result.path}"
            )
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "下载失败", f"下载模型时发生错误: {e}")

    def _on_refresh(self):
        try:
            self._model_manager.scan_models_dir()
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "刷新失败", f"刷新模型列表时发生错误: {e}")

    def _on_compare(self):
        selected = self._model_list_widget.get_selected_models()
        if len(selected) < 2:
            QMessageBox.information(self, "提示", "请先在列表中选择两个模型（按住 Ctrl 多选）")
            return
        model_a = selected[0]
        model_b = selected[1]
        QMessageBox.information(
            self, "模型对比",
            f"准备对比以下模型:\n"
            f"模型 A: {model_a.get('name', '-')} ({model_a.get('model_type', '-')})\n"
            f"模型 B: {model_b.get('name', '-')} ({model_b.get('model_type', '-')})\n\n"
            "模型对比功能需要指定测试图片或视频文件。\n该功能将在后续版本中完善。"
        )

    def _on_compare_selected(self, model_a, model_b):
        QMessageBox.information(
            self, "模型对比",
            f"准备对比以下模型:\n"
            f"模型 A: {model_a.get('name', '-')} ({model_a.get('model_type', '-')})\n"
            f"模型 B: {model_b.get('name', '-')} ({model_b.get('model_type', '-')})\n\n"
            "模型对比功能需要指定测试图片或视频文件。\n该功能将在后续版本中完善。"
        )

    def _on_delete(self, model_name):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模型 \"{model_name}\" 吗？\n此操作将删除模型文件，不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            success = self._model_manager.remove_model(model_name)
            if success:
                QMessageBox.information(self, "删除成功", f"模型 \"{model_name}\" 已删除")
            else:
                QMessageBox.warning(self, "删除失败", f"无法删除模型 \"{model_name}\"")
            self._refresh_models()
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"删除模型时发生错误: {e}")

    def _on_set_default(self, model_name):
        try:
            self._app_config.set("last_model", model_name)
            QMessageBox.information(
                self, "设置成功",
                f"已将 \"{model_name}\" 设为默认模型"
            )
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"保存默认模型时发生错误: {e}")
