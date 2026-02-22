from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _fmt_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class PlaylistsTab(QWidget):
    playlist_play_requested = Signal(list, bool)
    playlist_rename_requested = Signal(str, str)
    playlist_delete_requested = Signal(str)
    playlist_add_file_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks_by_path: dict[str, dict] = {}
        self._data: dict[str, Any] = {}
        self._active_key: tuple[str, str] | None = None

        self.smart_list = QListWidget()
        self.smart_list.addItems(["Recently Added", "Top 25 Most Played", "Favorites"])
        self.smart_list.currentItemChanged.connect(self._from_smart_selection)

        self.custom_list = QListWidget()
        self.custom_list.currentItemChanged.connect(self._from_custom_selection)

        self.play_btn = QPushButton("Play")
        self.shuffle_btn = QPushButton("Shuffle")
        self.edit_btn = QPushButton("Edit")
        self.add_file_btn = QPushButton("Add File")
        self.play_btn.clicked.connect(lambda: self._play(False))
        self.shuffle_btn.clicked.connect(lambda: self._play(True))
        self.edit_btn.clicked.connect(self._edit_selected)
        self.add_file_btn.clicked.connect(self._add_file_to_playlist)

        self.title = QLabel("No Playlist")
        self.title.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.summary = QLabel("0 tracks • 00:00")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Track", "Artist", "Album", "Duration", "Times Played"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        left = QVBoxLayout()
        left.addWidget(QLabel("Smart Playlists"))
        left.addWidget(self.smart_list)
        left.addWidget(QLabel("Playlists"))
        left.addWidget(self.custom_list)

        top_buttons = QHBoxLayout()
        top_buttons.addWidget(self.play_btn)
        top_buttons.addWidget(self.shuffle_btn)
        top_buttons.addWidget(self.edit_btn)
        top_buttons.addWidget(self.add_file_btn)
        top_buttons.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(self.title)
        right.addWidget(self.summary)
        right.addLayout(top_buttons)
        right.addWidget(self.table, 1)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addLayout(right, 3)

    def set_library_tracks(self, tracks: list[dict]) -> None:
        self._tracks_by_path = {t.get("path", ""): t for t in tracks}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = data
        self.custom_list.clear()
        for name in sorted(data.get("playlists", {}).keys(), key=str.lower):
            self.custom_list.addItem(name)

        if self._active_key is None:
            self.smart_list.setCurrentRow(0)
        else:
            self._load_active()

    def _from_smart_selection(self) -> None:
        item = self.smart_list.currentItem()
        if item is None:
            return
        label = item.text()
        key_map = {
            "Recently Added": "recently_added",
            "Top 25 Most Played": "top_25_most_played",
            "Favorites": "favorites",
        }
        key = key_map.get(label)
        if not key:
            return
        self._active_key = ("smart", key)
        self.custom_list.blockSignals(True)
        self.custom_list.clearSelection()
        self.custom_list.blockSignals(False)
        self._load_active()

    def _from_custom_selection(self) -> None:
        item = self.custom_list.currentItem()
        if item is None:
            return
        self.smart_list.blockSignals(True)
        self.smart_list.clearSelection()
        self.smart_list.blockSignals(False)
        self._active_key = ("custom", item.text())
        self._load_active()

    def _get_active_paths(self) -> list[str]:
        if self._active_key is None:
            return []

        bucket, key = self._active_key
        if bucket == "smart":
            return self._data.get("smart", {}).get(key, [])
        return self._data.get("playlists", {}).get(key, [])

    def _load_active(self) -> None:
        paths = self._get_active_paths()
        tracks = [self._tracks_by_path[p] for p in paths if p in self._tracks_by_path]

        if self._active_key is None:
            title = "No Playlist"
        elif self._active_key[0] == "smart":
            label_map = {
                "recently_added": "Recently Added",
                "top_25_most_played": "Top 25 Most Played",
                "favorites": "Favorites",
            }
            title = label_map.get(self._active_key[1], self._active_key[1])
        else:
            title = self._active_key[1]

        duration = sum(float(t.get("duration", 0.0)) for t in tracks)
        self.title.setText(title)
        self.summary.setText(f"{len(tracks)} tracks • {_fmt_duration(duration)}")

        play_counts = self._data.get("play_counts", {})
        self.table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            self.table.setItem(row, 0, QTableWidgetItem(track.get("title", "")))
            self.table.setItem(row, 1, QTableWidgetItem(track.get("artist", "")))
            self.table.setItem(row, 2, QTableWidgetItem(track.get("album", "")))
            self.table.setItem(row, 3, QTableWidgetItem(_fmt_duration(float(track.get("duration", 0.0)))))
            self.table.setItem(row, 4, QTableWidgetItem(str(play_counts.get(track.get("path", ""), 0))))

    def _play(self, shuffle: bool) -> None:
        paths = self._get_active_paths()
        if not paths:
            return
        self.playlist_play_requested.emit(paths, shuffle)

    def _edit_selected(self) -> None:
        if self._active_key is None or self._active_key[0] != "custom":
            QMessageBox.information(self, "Edit Playlist", "Select a custom playlist to edit.")
            return

        name = self._active_key[1]
        new_name, ok = QInputDialog.getText(self, "Rename Playlist", "Playlist name:", text=name)
        if ok and new_name and new_name != name:
            self.playlist_rename_requested.emit(name, new_name)
            return

        delete = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if delete == QMessageBox.StandardButton.Yes:
            self.playlist_delete_requested.emit(name)

    def _add_file_to_playlist(self) -> None:
        if self._active_key is None or self._active_key[0] != "custom":
            QMessageBox.information(self, "Add File", "Select a custom playlist first.")
            return
        self.playlist_add_file_requested.emit(self._active_key[1])
