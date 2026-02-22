from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _fmt_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class LibraryTab(QWidget):
    track_double_clicked = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[dict] = []

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, artist, album...")
        self.search.textChanged.connect(self._render)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Title", "Artist", "Album", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)

    def set_tracks(self, tracks: list[dict]) -> None:
        self._tracks = sorted(tracks, key=lambda t: (t.get("title") or "").lower())
        self._render()

    def _render(self) -> None:
        query = self.search.text().strip().lower()
        filtered = []
        if not query:
            filtered = self._tracks
        else:
            for track in self._tracks:
                text = " ".join(
                    [
                        str(track.get("title", "")),
                        str(track.get("artist", "")),
                        str(track.get("album", "")),
                    ]
                ).lower()
                if query in text:
                    filtered.append(track)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(filtered))
        for row, track in enumerate(filtered):
            title = QTableWidgetItem(track.get("title", ""))
            artist = QTableWidgetItem(track.get("artist", ""))
            album = QTableWidgetItem(track.get("album", ""))
            duration = QTableWidgetItem(_fmt_duration(float(track.get("duration", 0.0))))
            title.setData(Qt.ItemDataRole.UserRole, track)
            self.table.setItem(row, 0, title)
            self.table.setItem(row, 1, artist)
            self.table.setItem(row, 2, album)
            self.table.setItem(row, 3, duration)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)

    def _on_cell_double_clicked(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        track = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(track, dict):
            self.track_double_clicked.emit(track)
