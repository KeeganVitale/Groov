from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class NewTabWidget(QWidget):
    podcasts_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        button = QPushButton("Podcasts")
        button.setMinimumHeight(44)
        button.clicked.connect(self.podcasts_requested)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(button)
        layout.addStretch(1)
