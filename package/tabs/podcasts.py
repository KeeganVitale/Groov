from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.request import urlopen

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PodcastsTab(QWidget):
    episode_play_requested = Signal(dict, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._feeds: dict[str, dict] = {}

        self.podcast_list = QListWidget()
        self.podcast_list.currentItemChanged.connect(self._load_episodes)

        self.subscribe_btn = QPushButton("Subscribe")
        self.unsubscribe_btn = QPushButton("Unsubscribe")
        self.subscribe_btn.clicked.connect(self._subscribe)
        self.unsubscribe_btn.clicked.connect(self._unsubscribe)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Title", "Episode #", "Duration"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._play_episode)

        left = QVBoxLayout()
        left.addWidget(self.podcast_list, 1)
        left.addWidget(self.subscribe_btn)
        left.addWidget(self.unsubscribe_btn)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addWidget(self.table, 3)

    def _subscribe(self) -> None:
        url, ok = QInputDialog.getText(self, "Subscribe Podcast", "Feed URL:")
        url = url.strip()
        if not ok or not url:
            return

        try:
            data = self._fetch_feed(url.strip())
        except Exception as exc:
            QMessageBox.warning(self, "Subscribe", f"Failed to load feed: {exc}")
            return

        self._feeds[url] = data
        self.podcast_list.addItem(data.get("title", url))
        self.podcast_list.item(self.podcast_list.count() - 1).setData(Qt.ItemDataRole.UserRole, url)

    def _unsubscribe(self) -> None:
        row = self.podcast_list.currentRow()
        if row < 0:
            return
        item = self.podcast_list.takeItem(row)
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            self._feeds.pop(url, None)
        self.table.setRowCount(0)

    def _load_episodes(self) -> None:
        item = self.podcast_list.currentItem()
        if item is None:
            self.table.setRowCount(0)
            return

        url = item.data(Qt.ItemDataRole.UserRole)
        feed = self._feeds.get(url, {})
        episodes = feed.get("episodes", [])

        self.table.setRowCount(len(episodes))
        for row, ep in enumerate(episodes):
            title = QTableWidgetItem(ep.get("title", ""))
            ep_no = QTableWidgetItem(ep.get("episode", "-"))
            duration = QTableWidgetItem(ep.get("duration_label", "--:--"))
            title.setData(Qt.ItemDataRole.UserRole, ep)
            self.table.setItem(row, 0, title)
            self.table.setItem(row, 1, ep_no)
            self.table.setItem(row, 2, duration)

    def _play_episode(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        episode = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(episode, dict):
            return
        queue = [episode]
        self.episode_play_requested.emit(episode, queue)

    @staticmethod
    def _fetch_feed(url: str) -> dict:
        xml_text = urlopen(url, timeout=10).read().decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)

        channel = root.find("channel")
        if channel is None:
            raise ValueError("Invalid RSS feed")

        title = channel.findtext("title", default=url).strip()
        episodes: list[dict] = []
        for idx, item in enumerate(channel.findall("item"), start=1):
            ep_title = item.findtext("title", default=f"Episode {idx}").strip()
            enclosure = item.find("enclosure")
            media_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
            duration = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration", default="--:--")
            episode_no = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}episode", default=str(idx))
            if not media_url:
                continue
            episodes.append(
                {
                    "path": media_url,
                    "title": ep_title,
                    "artist": title,
                    "album": "Podcast",
                    "year": "",
                    "duration": 0.0,
                    "cover_art_path": "",
                    "composer": "",
                    "episode": episode_no,
                    "duration_label": duration,
                }
            )

        return {"title": title, "episodes": episodes}
