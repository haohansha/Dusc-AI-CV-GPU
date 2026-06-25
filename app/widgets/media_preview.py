from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QSplitter, QMenu, QAction, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
import cv2


class MediaPreviewWidget(QWidget):
    media_selected = pyqtSignal(dict)
    extract_frames_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_data = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self._list_widget = QListWidget()
        self.media_list = self._list_widget
        self._list_widget.setSelectionMode(QListWidget.SingleSelection)
        self._list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._list_widget.currentRowChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list_widget)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumSize(480, 360)
        self._preview_label.setStyleSheet(
            "QLabel { border: 1px solid #cccccc; background-color: #f5f5f5; }"
        )
        preview_layout.addWidget(self._preview_label)
        splitter.addWidget(preview_container)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def _on_selection_changed(self, row):
        if row < 0 or row >= len(self._media_data):
            return
        info = self._media_data[row]
        self.media_selected.emit(info)
        self.show_preview(info)

    def _on_context_menu(self, pos):
        item = self._list_widget.itemAt(pos)
        if item is None:
            return
        row = self._list_widget.row(item)
        if row < 0 or row >= len(self._media_data):
            return

        info = self._media_data[row]
        menu = QMenu(self)

        if info.get("media_type") == "video":
            extract_action = QAction("抽帧", self)
            extract_action.triggered.connect(lambda: self.extract_frames_requested.emit(info))
            menu.addAction(extract_action)

        open_folder_action = QAction("打开文件夹", self)
        open_folder_action.triggered.connect(lambda: self._open_folder(info))
        menu.addAction(open_folder_action)

        menu.exec_(self._list_widget.viewport().mapToGlobal(pos))

    def _open_folder(self, info):
        path = info.get("path", "")
        if path:
            import os
            folder = str(Path(path).parent)
            os.startfile(folder)

    def load_media(self, media_list):
        self._media_data = media_list
        self._list_widget.clear()
        for media in media_list:
            item = QListWidgetItem(media.get("name", ""))
            self._list_widget.addItem(item)

    def show_preview(self, media_info):
        media_type = media_info.get("media_type", "")
        path = media_info.get("path", "")

        if not path:
            self._preview_label.clear()
            return

        if media_type == "image":
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self._preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._preview_label.setPixmap(scaled)
            else:
                self._preview_label.setText("无法加载图片")
        elif media_type == "video":
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                import numpy as np
                from PyQt5.QtGui import QImage
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                if ch == 3:
                    q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                else:
                    q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(q_img)
                scaled = pixmap.scaled(
                    self._preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._preview_label.setPixmap(scaled)
            else:
                self._preview_label.setText("无法读取视频")

    def clear_preview(self):
        self._preview_label.clear()
