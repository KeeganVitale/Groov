from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal


_TIMESTAMP_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")


class LyricsFetcher(QObject):
    lyrics_changed = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[tuple[float, str]] = []

    @property
    def entries(self) -> list[tuple[float, str]]:
        return self._entries

    def load_for_track(self, track_path: str) -> list[tuple[float, str]]:
        path = Path(track_path)
        lrc_path = path.with_suffix(".lrc")
        txt_path = path.with_suffix(".txt")

        if lrc_path.exists():
            text = lrc_path.read_text(encoding="utf-8", errors="ignore")
            self._entries = self._parse_lrc(text)
        elif txt_path.exists():
            lines = txt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            self._entries = [(idx * 3.0, line.strip()) for idx, line in enumerate(lines) if line.strip()]
        else:
            self._entries = [(0.0, "No synced lyrics found")]

        self.lyrics_changed.emit(self._entries)
        return self._entries

    @staticmethod
    def _parse_lrc(text: str) -> list[tuple[float, str]]:
        out: list[tuple[float, str]] = []
        for line in text.splitlines():
            matches = list(_TIMESTAMP_RE.finditer(line))
            lyric = _TIMESTAMP_RE.sub("", line).strip()
            if not matches:
                continue
            if not lyric:
                lyric = "..."
            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                millis_str = match.group(3) or "0"
                millis = int(millis_str.ljust(3, "0")[:3])
                ts = minutes * 60 + seconds + (millis / 1000)
                out.append((ts, lyric))

        out.sort(key=lambda t: t[0])
        return out or [(0.0, "No synced lyrics found")]
