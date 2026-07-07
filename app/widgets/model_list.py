from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMenu, QAction, QMessageBox, QAbstractItemView)
from PyQt5.QtCore import pyqtSignal, Qt


def _format_file_size(size_bytes):
    if size_bytes is None:
        return "-"
    size_bytes = float(size_bytes)
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / 1024:.1f} KB"


class ModelListWidget(QWidget):
    model_selected = pyqtSignal(dict)
    model_double_clicked = pyqtSignal(dict)
    import_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    compare_clicked = pyqtSignal(dict, dict)
    delete_requested = pyqtSignal(str)
    set_default_requested = pyqtSignal(str)

    COLUMNS = ["名称", "类型", "类别数", "大小", "创建时间", "状态"]

    def __init__(self, parent=None, show_toolbar=True):
        super().__init__(parent)
        self._models_data = []
        self._show_toolbar = show_toolbar
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if self._show_toolbar:
            toolbar_layout = QHBoxLayout()

            self._import_btn = QPushButton("导入模型")
            self._import_btn.clicked.connect(self.import_clicked)
            toolbar_layout.addWidget(self._import_btn)

            self._refresh_btn = QPushButton("刷新")
            self._refresh_btn.clicked.connect(self.refresh_clicked)
            toolbar_layout.addWidget(self._refresh_btn)

            toolbar_layout.addStretch()
            layout.addLayout(toolbar_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellDoubleClicked.connect(self._on_double_clicked)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self._table)

    def _on_selection_changed(self):
        selected = self._table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        if row < len(self._models_data):
            self.model_selected.emit(self._models_data[row])

    def _on_double_clicked(self, row, column):
        if row < len(self._models_data):
            self.model_double_clicked.emit(self._models_data[row])

    def _on_context_menu(self, pos):
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        menu = QMenu(self)

        detail_action = QAction("查看详情", self)
        detail_action.triggered.connect(self._on_detail)
        menu.addAction(detail_action)

        compare_action = QAction("模型对比", self)
        compare_action.triggered.connect(self._on_compare)
        menu.addAction(compare_action)

        delete_action = QAction("删除模型", self)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)

        set_default_action = QAction("设为默认", self)
        set_default_action.triggered.connect(self._on_set_default)
        menu.addAction(set_default_action)

        menu.exec_(self._table.viewport().mapToGlobal(pos))

    def _on_detail(self):
        selected = self.get_selected_models()
        if selected:
            info = selected[0]
            QMessageBox.information(
                self, "模型详情",
                f"名称: {info.get('name', '-')}\n"
                f"类型: {info.get('model_type', '-')}\n"
                f"类别数: {info.get('num_classes', '-')}\n"
                f"大小: {_format_file_size(info.get('file_size'))}\n"
                f"创建时间: {info.get('created_at', '-')}\n"
                f"状态: {info.get('status', '-')}"
            )

    def _on_compare(self):
        selected = self.get_selected_models()
        if len(selected) < 2:
            QMessageBox.warning(self, "提示", "请至少选择两个模型进行对比")
            return
        self.compare_clicked.emit(selected[0], selected[1])

    def _on_delete(self):
        selected = self.get_selected_models()
        if not selected:
            return
        for info in selected:
            self.delete_requested.emit(info.get("name", ""))

    def _on_set_default(self):
        selected = self.get_selected_models()
        if not selected:
            return
        self.set_default_requested.emit(selected[0].get("name", ""))

    def load_models(self, models_list):
        self._models_data = models_list
        self._table.setRowCount(0)
        self._table.setRowCount(len(models_list))
        for row, model in enumerate(models_list):
            self._table.setItem(row, 0, QTableWidgetItem(str(model.get("name", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(model.get("model_type", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(model.get("num_classes", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(_format_file_size(model.get("file_size"))))
            self._table.setItem(row, 4, QTableWidgetItem(str(model.get("created_at", ""))))
            self._table.setItem(row, 5, QTableWidgetItem(str(model.get("status", ""))))

    def get_selected_models(self):
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())
        result = []
        for row in selected_rows:
            if row < len(self._models_data):
                result.append(self._models_data[row])
        return result
