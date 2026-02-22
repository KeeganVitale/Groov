from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class ViewMenu:
    def __init__(self, menu_bar: QMenuBar) -> None:
        menu = menu_bar.addMenu("View")

        self.toggle_library = QAction("Show Library Tab", menu, checkable=True)
        self.toggle_library.setChecked(True)
        self.toggle_explorer = QAction("Show Music Explorer Tab", menu, checkable=True)
        self.toggle_explorer.setChecked(True)
        self.toggle_now_playing = QAction("Show Now Playing Tab", menu, checkable=True)
        self.toggle_now_playing.setChecked(True)
        self.toggle_playlists = QAction("Show Playlists Tab", menu, checkable=True)
        self.toggle_playlists.setChecked(True)
        self.toggle_podcasts = QAction("Show Podcasts Tab", menu, checkable=True)
        self.toggle_podcasts.setChecked(True)

        self.toggle_spectrum = QAction("Show Now Playing Spectrum", menu, checkable=True)
        self.toggle_spectrum.setChecked(True)

        menu.addAction(self.toggle_library)
        menu.addAction(self.toggle_explorer)
        menu.addAction(self.toggle_now_playing)
        menu.addAction(self.toggle_playlists)
        menu.addAction(self.toggle_podcasts)
        menu.addSeparator()
        menu.addAction(self.toggle_spectrum)
