from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class ToolsMenu:
    def __init__(self, menu_bar: QMenuBar) -> None:
        menu = menu_bar.addMenu("Tools")
        tagging = menu.addMenu("Tagging Tools")
        self.show_missing_metadata = QAction("Show files with missing metadata", tagging)
        tagging.addAction(self.show_missing_metadata)
