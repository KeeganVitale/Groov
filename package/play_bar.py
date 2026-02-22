from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    mins = total // 60
    secs = total % 60
    return f"{mins:02d}:{secs:02d}"


class TinyGridVu(QWidget):
    def __init__(self, columns: int = 12, rows: int = 6, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = columns
        self._rows = rows
        self._gain = 1.8
        self._levels = [0.0] * columns
        self.setFixedSize(88, 34)

    def set_levels(self, values: list[float]) -> None:
        if not values:
            self._levels = [0.0] * self._columns
            self.update()
            return
        step = max(1, len(values) // self._columns)
        out: list[float] = []
        for i in range(self._columns):
            chunk = values[i * step : (i + 1) * step]
            raw = (sum(chunk) / len(chunk)) if chunk else 0.0
            out.append(max(0.0, min(1.0, raw * self._gain)))
        self._levels = out
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect().adjusted(1, 1, -1, -1)
        cw = rect.width() / self._columns
        ch = rect.height() / self._rows

        off = QColor("#2f333c")
        on = QColor("#4ad66d")
        peak = QColor("#f2c14e")

        for col in range(self._columns):
            active = int(max(0.0, min(1.0, self._levels[col])) * self._rows)
            for row in range(self._rows):
                x = int(rect.left() + col * cw + 1)
                y = int(rect.bottom() - (row + 1) * ch + 1)
                w = max(1, int(cw - 2))
                h = max(1, int(ch - 2))
                color = off
                if row < active:
                    color = peak if row >= self._rows - 1 else on
                painter.fillRect(x, y, w, h, color)


class PlayBar(QWidget):
    previous_clicked = Signal()
    play_pause_clicked = Signal()
    next_clicked = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._duration = 0.0
        self._is_playing = False
        self._seeking = False
        assets_dir = Path(__file__).resolve().parent.parent / "assets" / "status icons"
        self._music_on_icon = QPixmap(str(assets_dir / "music_on.png"))
        self._music_off_icon = QPixmap(str(assets_dir / "music_off.png"))

        self.setObjectName("playBar")
        self.setStyleSheet(
            """
            QWidget#playBar { background: #17191d; border-top: 1px solid #2e323b; }
            QLabel { color: #e6e8eb; }
            QPushButton { background: #252a33; border: 1px solid #3a404c; border-radius: 5px; color: #f3f4f6; padding: 5px; }
            QPushButton:hover { background: #303746; }
            QSlider::groove:horizontal { height: 6px; background: #2b2f39; border-radius: 3px; }
            QSlider::handle:horizontal { background: #f2c14e; width: 14px; margin: -4px 0; border-radius: 7px; }
            """
        )

        self.vu = TinyGridVu()
        self.cover = QLabel()
        self.cover.setFixedSize(52, 52)
        self.cover.setStyleSheet("background: #2a2f39; border-radius: 4px;")

        self.title = QLabel("No Track")
        self.title.setStyleSheet("font-weight: 700;")
        self.artist = QLabel("-")

        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 0)
        self.progress.sliderPressed.connect(self._on_seek_start)
        self.progress.sliderReleased.connect(self._on_seek_end)

        self.time_label = QLabel("00:00 / 00:00")

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.prev_btn.clicked.connect(self.previous_clicked)
        self.play_btn.clicked.connect(self.play_pause_clicked)
        self.next_btn.clicked.connect(self.next_clicked)

        self.volume_icon = QLabel()
        self.volume_icon.setFixedSize(20, 20)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_value = QLabel("75")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.title)
        info_layout.addWidget(self.artist)

        middle = QVBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(4)
        middle.addLayout(controls)
        middle.addWidget(self.progress)

        timeline = QHBoxLayout()
        timeline.addStretch(1)
        timeline.addWidget(self.time_label)
        middle.addLayout(timeline)

        top = QHBoxLayout(self)
        top.setContentsMargins(10, 8, 10, 8)
        top.setSpacing(10)
        top.addWidget(self.vu)
        top.addWidget(self.cover)
        top.addLayout(info_layout)
        top.addLayout(middle, 1)

        vol_col = QHBoxLayout()
        vol_col.setSpacing(6)
        vol_col.addWidget(self.volume_icon)
        vol_col.addWidget(self.volume_slider)
        vol_col.addWidget(self.volume_value)
        top.addLayout(vol_col)

        self._update_volume_icon(75)

    def set_track_info(self, title: str, artist: str, cover_path: str = "") -> None:
        self.title.setText(title or "Unknown Title")
        self.artist.setText(artist or "Unknown Artist")

        pix = QPixmap(cover_path) if cover_path else QPixmap()
        if pix.isNull():
            pix = QPixmap(self.cover.size())
            pix.fill(QColor("#2a2f39"))
            painter = QPainter(pix)
            painter.setPen(QPen(QColor("#5b6270"), 2))
            painter.drawLine(QPointF(8, 8), QPointF(44, 44))
            painter.drawLine(QPointF(44, 8), QPointF(8, 44))
            painter.end()
        self.cover.setPixmap(pix.scaled(self.cover.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))

    def set_playing(self, playing: bool) -> None:
        self._is_playing = playing
        self.play_btn.setText("⏸" if playing else "▶")

    def set_position(self, position: float, duration: float) -> None:
        self._duration = max(duration, 0.0)
        if not self._seeking:
            self.progress.setRange(0, int(self._duration * 1000))
            self.progress.setValue(int(max(position, 0.0) * 1000))
        self.time_label.setText(f"{format_time(position)} / {format_time(duration)}")

    def update_spectrum(self, values: list[float]) -> None:
        self.vu.set_levels(values)

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self.seek_requested.emit(self.progress.value() / 1000.0)

    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(str(value))
        self._update_volume_icon(value)
        self.volume_changed.emit(value / 100.0)

    def _update_volume_icon(self, value: int) -> None:
        pix = self._music_off_icon if value == 0 else self._music_on_icon
        if pix.isNull():
            self.volume_icon.setText("🔇" if value == 0 else "🔊")
            return
        self.volume_icon.setText("")
        self.volume_icon.setPixmap(
            pix.scaled(
                self.volume_icon.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
