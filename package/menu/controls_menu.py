from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class ControlsMenu:
    def __init__(self, menu_bar: QMenuBar) -> None:
        menu = menu_bar.addMenu("Controls")

        self.dsp_effects = QAction("DSP Effects", menu)
        self.dynamic_effects = QAction("Dynamic Effects", menu)
        self.repeat = QAction("Repeat", menu, checkable=True)
        self.shuffle = QAction("Shuffle", menu, checkable=True)
        self.stop = QAction("Stop", menu)
        self.play_pause = QAction("Play / Pause", menu)
        self.next_track = QAction("Next Track", menu)

        menu.addAction(self.dsp_effects)
        menu.addAction(self.dynamic_effects)
        menu.addSeparator()
        menu.addAction(self.repeat)
        menu.addAction(self.shuffle)
        menu.addAction(self.stop)
        menu.addAction(self.play_pause)
        menu.addAction(self.next_track)
