from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SpectrumVisualizer(QWidget):
    def __init__(self, bands: int = 128, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bands = bands
        self._values = [0.0] * bands
        self._caps = [0.0] * bands
        self.setMinimumHeight(130)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_values(self, values: list[float]) -> None:
        if len(values) < self._bands:
            values = values + [0.0] * (self._bands - len(values))
        self._values = values[: self._bands]
        for i in range(self._bands):
            self._caps[i] = max(self._values[i], self._caps[i] - 0.02)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0f1115"))

        w = self.width()
        h = self.height()
        bar_w = max(1, w / self._bands)

        p.setPen(Qt.PenStyle.NoPen)
        for i, val in enumerate(self._values):
            bh = int(val * (h - 10))
            x = int(i * bar_w)
            y = h - bh
            p.setBrush(QColor("#4ad66d"))
            p.drawRect(x, y, max(1, int(bar_w - 1)), bh)

            cap_y = int(h - self._caps[i] * (h - 10))
            p.setBrush(QColor("#f2c14e"))
            p.drawRect(x, cap_y, max(1, int(bar_w - 1)), 2)


class NowPlayingTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lyrics: list[tuple[float, str]] = []
        self._active_lyric_index = -1
        self._latest_spectrum: list[float] | None = None

        self.cover = QLabel()
        self.cover.setFixedSize(180, 180)
        self.cover.setStyleSheet("background: #232730; border-radius: 8px;")

        self.title = QLabel("No Track")
        self.title.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.artist = QLabel("-")
        self.album_year = QLabel("-")

        self.lyrics_list = QListWidget()
        self.lyrics_list.setStyleSheet(
            """
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background: #2e3440; font-weight: 700; }
            """
        )

        self.visualizer = SpectrumVisualizer(128)
        self.sample_rate = QSlider(Qt.Orientation.Horizontal)
        self.sample_rate.setRange(8, 48)
        self.sample_rate.setValue(24)
        self.sample_rate_label = QLabel("Sampling Rate: 24 kHz")
        self.sample_rate.valueChanged.connect(
            lambda v: self.sample_rate_label.setText(f"Sampling Rate: {v} kHz")
        )

        self._visualizer_timer = QTimer(self)
        self._visualizer_timer.setInterval(28)
        self._visualizer_timer.timeout.connect(self._render_latest_spectrum)
        self._visualizer_timer.start()

        top = QHBoxLayout()
        top.addWidget(self.cover)

        info = QVBoxLayout()
        info.addWidget(self.title)
        info.addWidget(self.artist)
        info.addWidget(self.album_year)
        info.addStretch(1)
        top.addLayout(info, 1)

        vis_controls = QHBoxLayout()
        vis_controls.addWidget(self.sample_rate_label)
        vis_controls.addWidget(self.sample_rate)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(QLabel("Lyrics"))
        layout.addWidget(self.lyrics_list, 1)
        layout.addWidget(self.visualizer)
        layout.addLayout(vis_controls)

    def set_track(self, track: dict) -> None:
        title = str(track.get("title") or "Unknown Title")
        artist = str(track.get("artist") or "Unknown Artist")
        album = str(track.get("album") or "Unknown Album")
        year = str(track.get("year") or "")

        self.title.setText(title)
        self.artist.setText(artist)
        year_text = f" [{year}]" if year else ""
        self.album_year.setText(f"{album}{year_text}")

        cover_art_path = str(track.get("cover_art_path") or "")
        pix = QPixmap(cover_art_path)
        if pix.isNull():
            pix = QPixmap(self.cover.size())
            pix.fill(QColor("#232730"))
            p = QPainter(pix)
            p.setPen(QPen(QColor("#5b6270"), 2))
            p.drawRect(12, 12, pix.width() - 24, pix.height() - 24)
            p.end()
        self.cover.setPixmap(
            pix.scaled(
                self.cover.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def set_lyrics(self, lines: list[tuple[float, str]]) -> None:
        self._lyrics = lines
        self._active_lyric_index = -1
        self.lyrics_list.clear()
        for _ts, text in lines:
            item = QListWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.lyrics_list.addItem(item)
        if self.lyrics_list.count() > 0:
            self.lyrics_list.setCurrentRow(0)

    def set_position(self, position_seconds: float) -> None:
        if not self._lyrics:
            return
        idx = 0
        for i, (timestamp, _text) in enumerate(self._lyrics):
            if timestamp <= position_seconds:
                idx = i
            else:
                break
        if idx == self._active_lyric_index:
            return
        self._active_lyric_index = idx
        self.lyrics_list.setCurrentRow(idx)
        item = self.lyrics_list.item(idx)
        if item is not None:
            self.lyrics_list.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)

    def set_spectrum(self, values: list[float]) -> None:
        self._latest_spectrum = self._with_extra_low_bands(values)

    def set_visualizer_fps(self, fps: int) -> None:
        fps = max(8, min(60, int(fps)))
        self._visualizer_timer.setInterval(max(1, int(1000 / fps)))

    def _render_latest_spectrum(self) -> None:
        if self._latest_spectrum is None:
            return
        self.visualizer.set_values(self._latest_spectrum)

    def _with_extra_low_bands(self, values: list[float]) -> list[float]:
        if len(values) < 16:
            return values[:]

        total = len(values)
        # Allocate more on-screen bars to the lowest frequencies for clearer bass activity.
        low_source = max(4, int(total * 0.18))
        low_target = max(10, int(total * 0.30))
        low_target = min(low_target, total - 1)

        lows = self._resample_bands(values[:low_source], low_target)
        highs = self._resample_bands(values[low_source:], total - low_target)
        return lows + highs

    @staticmethod
    def _resample_bands(values: list[float], target: int) -> list[float]:
        if target <= 0:
            return []
        if not values:
            return [0.0] * target
        if len(values) == target:
            return values[:]

        n = len(values)
        out: list[float] = []
        for i in range(target):
            start = int(i * n / target)
            end = int((i + 1) * n / target)
            if end <= start:
                end = min(n, start + 1)
            chunk = values[start:end]
            out.append((sum(chunk) / len(chunk)) if chunk else values[min(start, n - 1)])
        return out
