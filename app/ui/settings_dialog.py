from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QDialogButtonBox, QHBoxLayout)
from app.models.app_config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("设置")
        self.setMinimumWidth(520)

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._model_dir_edit = QLineEdit()
        self._model_dir_btn = QPushButton("浏览")
        self._model_dir_btn.clicked.connect(self._browse_model_dir)
        model_row = QHBoxLayout()
        model_row.addWidget(self._model_dir_edit)
        model_row.addWidget(self._model_dir_btn)
        form.addRow("默认模型目录", model_row)

        self._data_dir_edit = QLineEdit()
        self._data_dir_btn = QPushButton("浏览")
        self._data_dir_btn.clicked.connect(self._browse_data_dir)
        data_row = QHBoxLayout()
        data_row.addWidget(self._data_dir_edit)
        data_row.addWidget(self._data_dir_btn)
        form.addRow("默认数据目录", data_row)

        self._output_dir_edit = QLineEdit()
        self._output_dir_btn = QPushButton("浏览")
        self._output_dir_btn.clicked.connect(self._browse_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_dir_edit)
        output_row.addWidget(self._output_dir_btn)
        form.addRow("默认输出目录", output_row)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["亮色", "暗色"])
        form.addRow("主题", self._theme_combo)

        self._language_combo = QComboBox()
        self._language_combo.addItems(["中文"])
        form.addRow("语言", self._language_combo)

        layout.addLayout(form)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def _load_config(self):
        model_dir = self._config.get("default_model_dir", "models")
        self._model_dir_edit.setText(model_dir)

        data_dir = self._config.get("default_data_dir", "data/media")
        self._data_dir_edit.setText(data_dir)

        output_dir = self._config.get("default_output_dir", "runs")
        self._output_dir_edit.setText(output_dir)

        theme = self._config.get("theme", "light")
        if theme == "dark":
            self._theme_combo.setCurrentText("暗色")
        else:
            self._theme_combo.setCurrentText("亮色")

        language = self._config.get("language", "zh_CN")
        if language == "zh_CN":
            self._language_combo.setCurrentText("中文")

    def _browse_model_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择模型目录", self._model_dir_edit.text())
        if directory:
            self._model_dir_edit.setText(directory)

    def _browse_data_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择数据目录", self._data_dir_edit.text())
        if directory:
            self._data_dir_edit.setText(directory)

    def _browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录", self._output_dir_edit.text())
        if directory:
            self._output_dir_edit.setText(directory)

    _THEME_MAP = {"亮色": "light", "暗色": "dark"}

    _LANGUAGE_MAP = {"中文": "zh_CN"}

    def _on_accept(self):
        self._config.set("default_model_dir", self._model_dir_edit.text())
        self._config.set("default_data_dir", self._data_dir_edit.text())
        self._config.set("default_output_dir", self._output_dir_edit.text())

        theme_text = self._theme_combo.currentText()
        self._config.set("theme", self._THEME_MAP.get(theme_text, "light"))

        language_text = self._language_combo.currentText()
        self._config.set("language", self._LANGUAGE_MAP.get(language_text, "zh_CN"))

        self._config.save()
        self.accept()
