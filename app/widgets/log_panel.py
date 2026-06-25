from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

LEVEL_COLORS = {
    "INFO": "#000000",
    "WARNING": "#FF8C00",
    "ERROR": "#FF0000",
    "SUCCESS": "#008000",
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.Monospace)
        self._text_edit.setFont(font)
        layout.addWidget(self._text_edit)

    def append_log(self, message, level="INFO"):
        color = LEVEL_COLORS.get(level, "#000000")
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        html = (
            f'<span style="color:{color};">'
            f"{timestamp} [{level}] {message}"
            f"</span><br>"
        )
        self._text_edit.append(html)
        scrollbar = self._text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        self._text_edit.clear()
