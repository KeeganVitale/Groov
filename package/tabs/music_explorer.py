from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)


def _fmt_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class MusicExplorerTab(QWidget):
    album_play_requested = Signal(list, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[dict] = []
        self._play_counts: dict[str, int] = {}
        self._artists: dict[str, list[dict]] = {}
        self._albums_by_artist: dict[str, dict[str, list[dict]]] = {}

        self.counters = {
            "Artists": QLabel("0"),
            "Albums": QLabel("0"),
            "Tracks": QLabel("0"),
            "Composers": QLabel("0"),
        }

        counter_layout = QGridLayout()
        for idx, (name, label) in enumerate(self.counters.items()):
            box = QGroupBox(name)
            inner = QVBoxLayout(box)
            label.setStyleSheet("font-size: 20px; font-weight: 700;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(label)
            counter_layout.addWidget(box, 0, idx)

        self.artists_list = QListWidget()
        self.artists_list.currentItemChanged.connect(self._on_artist_selected)

        self.albums_list = QListWidget()
        self.albums_list.itemDoubleClicked.connect(self._play_selected_album)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Artists"))
        left_layout.addWidget(self.artists_list, 2)
        left_layout.addWidget(QLabel("Albums"))
        left_layout.addWidget(self.albums_list, 2)

        self.artist_cover = QLabel()
        self.artist_cover.setFixedSize(92, 92)
        self.artist_cover.setStyleSheet("background: #232730; border-radius: 8px;")

        self.artist_name = QLabel("No Artist")
        self.artist_name.setStyleSheet("font-size: 20px; font-weight: 700;")

        self.artist_stats = QLabel("Plays:0 • 0 Albums / 0 Tracks")

        header = QHBoxLayout()
        header.addWidget(self.artist_cover)
        header_right = QVBoxLayout()
        header_right.addWidget(self.artist_name)
        header_right.addWidget(self.artist_stats)
        header_right.addStretch(1)
        header.addLayout(header_right, 1)

        self.albums_table = QTableWidget(0, 3)
        self.albums_table.setHorizontalHeaderLabels(["Album", "Tracks", "Plays"])
        self.albums_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.albums_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.albums_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.albums_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.albums_table.cellDoubleClicked.connect(self._play_album_from_table)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addLayout(header)
        center_layout.addWidget(QLabel("Albums"))
        center_layout.addWidget(self.albums_table, 1)

        self.top_tracks_list = QListWidget()
        top_tracks_wrap = QWidget()
        top_tracks_layout = QVBoxLayout(top_tracks_wrap)
        top_tracks_layout.addWidget(QLabel("TOP TRACKS"))
        top_tracks_layout.addWidget(self.top_tracks_list, 1)

        right_split = QSplitter(Qt.Orientation.Horizontal)
        right_split.addWidget(center)
        right_split.addWidget(top_tracks_wrap)
        right_split.setSizes([820, 260])

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(right_split)
        split.setSizes([320, 960])

        layout = QVBoxLayout(self)
        layout.addLayout(counter_layout)
        layout.addWidget(split, 1)

    def set_tracks(self, tracks: list[dict], play_counts: dict[str, int] | None = None) -> None:
        self._play_counts = play_counts or {}
        self._tracks = tracks

        artists = defaultdict(list)
        albums_by_artist: dict[str, dict[str, list[dict]]] = {}
        global_albums = set()

        for track in tracks:
            artist = str(track.get("artist") or "Unknown Artist")
            album = str(track.get("album") or "Unknown Album")
            artists[artist].append(track)
            albums_by_artist.setdefault(artist, defaultdict(list))[album].append(track)
            global_albums.add(album)

        self._artists = dict(artists)
        self._albums_by_artist = {
            a: dict(albums) for a, albums in albums_by_artist.items()
        }

        composers = {t.get("composer", "") for t in tracks if t.get("composer", "")}
        self.counters["Artists"].setText(str(len(self._artists)))
        self.counters["Albums"].setText(str(len(global_albums)))
        self.counters["Tracks"].setText(str(len(tracks)))
        self.counters["Composers"].setText(str(len(composers)))

        self.artists_list.clear()
        for artist in sorted(self._artists.keys(), key=str.lower):
            self.artists_list.addItem(artist)

        if self.artists_list.count() > 0:
            self.artists_list.setCurrentRow(0)
        else:
            self._reset_artist_view()

    def _on_artist_selected(self) -> None:
        item = self.artists_list.currentItem()
        if item is None:
            self._reset_artist_view()
            return

        artist = item.text()
        artist_tracks = self._artists.get(artist, [])
        albums = self._albums_by_artist.get(artist, {})

        self.artist_name.setText(artist)
        plays = sum(self._play_counts.get(str(t.get("path") or ""), 0) for t in artist_tracks)
        self.artist_stats.setText(
            f"Plays:{plays} • {len(albums)} Albums / {len(artist_tracks)} Tracks"
        )
        self._set_artist_cover(artist_tracks)

        self.albums_list.clear()
        for album in sorted(albums.keys(), key=str.lower):
            self.albums_list.addItem(album)

        self.albums_table.setRowCount(len(albums))
        for row, album in enumerate(sorted(albums.keys(), key=str.lower)):
            tracks = albums[album]
            album_plays = sum(self._play_counts.get(str(t.get("path") or ""), 0) for t in tracks)
            album_item = QTableWidgetItem(album)
            album_item.setData(Qt.ItemDataRole.UserRole, album)
            self.albums_table.setItem(row, 0, album_item)
            self.albums_table.setItem(row, 1, QTableWidgetItem(str(len(tracks))))
            self.albums_table.setItem(row, 2, QTableWidgetItem(str(album_plays)))

        top_tracks = sorted(
            artist_tracks,
            key=lambda t: self._play_counts.get(str(t.get("path") or ""), 0),
            reverse=True,
        )
        self.top_tracks_list.clear()
        for track in top_tracks[:25]:
            plays_count = self._play_counts.get(str(track.get("path") or ""), 0)
            label = f"{track.get('title', 'Unknown Title')} ({plays_count})"
            self.top_tracks_list.addItem(label)

    def _set_artist_cover(self, tracks: list[dict]) -> None:
        cover_path = ""
        for track in tracks:
            p = str(track.get("cover_art_path") or "")
            if p:
                cover_path = p
                break

        pix = QPixmap(cover_path)
        if pix.isNull():
            pix = QPixmap(self.artist_cover.size())
            pix.fill(QColor("#232730"))
            p = QPainter(pix)
            p.setPen(QPen(QColor("#5b6270"), 2))
            p.drawRect(10, 10, pix.width() - 20, pix.height() - 20)
            p.end()

        self.artist_cover.setPixmap(
            pix.scaled(
                self.artist_cover.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _play_selected_album(self, item: QListWidgetItem) -> None:
        artist_item = self.artists_list.currentItem()
        if artist_item is None:
            return
        artist = artist_item.text()
        album = item.text()
        tracks = self._albums_by_artist.get(artist, {}).get(album, [])
        if tracks:
            self.album_play_requested.emit(tracks, True)

    def _play_album_from_table(self, row: int, _column: int) -> None:
        artist_item = self.artists_list.currentItem()
        if artist_item is None:
            return
        album_item = self.albums_table.item(row, 0)
        if album_item is None:
            return
        artist = artist_item.text()
        album = str(album_item.data(Qt.ItemDataRole.UserRole) or album_item.text())
        tracks = self._albums_by_artist.get(artist, {}).get(album, [])
        if tracks:
            self.album_play_requested.emit(tracks, True)

    def _reset_artist_view(self) -> None:
        self.artist_name.setText("No Artist")
        self.artist_stats.setText("Plays:0 • 0 Albums / 0 Tracks")
        self.albums_list.clear()
        self.albums_table.setRowCount(0)
        self.top_tracks_list.clear()
        self._set_artist_cover([])
