"""可复用界面组件。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout


class StatusDot(QWidget):
    """彩色状态圆点，用于直观展示监听/连接状态。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._label = QLabel("●")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("color: #999; font-size: 18px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

    def set_color(self, color: str) -> None:
        self._label.setStyleSheet(f"color: {color}; font-size: 18px;")


__all__ = ["StatusDot"]