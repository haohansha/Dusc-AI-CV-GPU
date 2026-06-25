from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt
from app.widgets.media_preview import MediaPreviewWidget


class DataPage(QWidget):
    def __init__(self, project_root: Path, dataset_manager):
        super().__init__()
        self.project_root = project_root
        self.dataset_manager = dataset_manager
        self._setup_ui()
        self._refresh_media()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.btn_import_video = QPushButton("导入视频")
        self.btn_import_video.clicked.connect(self._on_import_video)
        toolbar.addWidget(self.btn_import_video)

        self.btn_import_image = QPushButton("导入图片")
        self.btn_import_image.clicked.connect(self._on_import_image)
        toolbar.addWidget(self.btn_import_image)

        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.media_preview = MediaPreviewWidget()
        self.media_preview.media_selected.connect(self._on_media_selected)
        self.media_preview.extract_frames_requested.connect(self._on_extract_frames_requested)
        layout.addWidget(self.media_preview)

    def _on_media_selected(self, info):
        pass

    def _on_import_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov)"
        )
        if not path:
            return
        try:
            self.dataset_manager.import_video(path)
            self._refresh_media()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入视频失败:\n{str(e)}")

    def _on_import_image(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "", "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        if not paths:
            return
        try:
            self.dataset_manager.import_images(paths)
            self._refresh_media()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入图片失败:\n{str(e)}")

    def _on_delete(self):
        name = self._get_selected_media_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择要删除的媒体")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 \"{name}\" 吗？\n此操作将同时删除文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.dataset_manager.remove_media(name, delete_file=True)
            self._refresh_media()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除媒体失败:\n{str(e)}")

    def _on_extract_frames_requested(self, info):
        interval, ok = QInputDialog.getInt(
            self, "抽帧间隔", "请输入抽帧间隔（帧）:", 15, 1, 300
        )
        if not ok:
            return
        try:
            media_path = self.project_root / info.get("path", "")
            count = self.dataset_manager.extract_frames(str(media_path), interval)
            QMessageBox.information(self, "抽帧完成", f"成功抽取 {count} 帧。")
        except Exception as e:
            QMessageBox.critical(self, "抽帧失败", f"抽帧失败:\n{str(e)}")

    def _get_selected_media_name(self):
        current = self.media_preview.media_list.currentItem()
        if current:
            return current.text()
        return None

    def _refresh_media(self):
        media_list = self.dataset_manager.list_media()
        data = []
        for m in media_list:
            data.append({
                "name": m.name,
                "media_type": m.media_type,
                "path": str(self.project_root / m.path),
            })
        self.media_preview.load_media(data)
