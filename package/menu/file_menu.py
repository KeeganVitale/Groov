from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class FileMenu:
    def __init__(self, menu_bar: QMenuBar) -> None:
        menu = menu_bar.addMenu("File")

        self.add_folder = QAction("Add Folder", menu)
        self.add_file = QAction("Add File", menu)
        self.stream_url = QAction("Stream URL", menu)
        self.remove_folder = QAction("Remove Folder", menu)

        menu.addAction(self.add_folder)
        menu.addAction(self.add_file)

        playlists = menu.addMenu("Playlists")
        self.add_playlist = QAction("Add Playlist", playlists)
        self.recently_added = QAction("Recently Added", playlists)
        self.top_25 = QAction("Top 25 Most Played", playlists)
        self.favorites = QAction("Favorites", playlists)
        playlists.addAction(self.add_playlist)
        playlists.addSeparator()
        playlists.addAction(self.recently_added)
        playlists.addAction(self.top_25)
        playlists.addAction(self.favorites)

        menu.addSeparator()
        menu.addAction(self.stream_url)
        menu.addAction(self.remove_folder)
