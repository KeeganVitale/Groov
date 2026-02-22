from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal

from .metadata import AUDIO_EXTENSIONS, MetadataExtractor


class LibraryStore(QObject):
    library_changed = Signal(list)

    def __init__(self, data_file: str | Path) -> None:
        super().__init__()
        self._path = Path(data_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._extractor = MetadataExtractor()
        self._tracks: list[dict] = []
        self._folders: list[str] = []
        self.load()

    @property
    def tracks(self) -> list[dict]:
        return list(self._tracks)

    @property
    def folders(self) -> list[str]:
        return list(self._folders)

    def load(self) -> None:
        if not self._path.exists():
            self._write()
            return

        try:
            content = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        except Exception:
            content = {}

        self._folders = [str(Path(p)) for p in content.get("folders", [])]
        self._tracks = [
            t for t in content.get("tracks", []) if Path(t.get("path", "")).exists()
        ]
        if self._refresh_incomplete_metadata():
            self._write()
        self._sort_tracks()

    def _write(self) -> None:
        payload = {"folders": self._folders, "tracks": self._tracks}
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _sort_tracks(self) -> None:
        self._tracks.sort(key=lambda t: (t.get("title") or "").lower())

    def _refresh_incomplete_metadata(self) -> bool:
        changed = False
        for idx, track in enumerate(self._tracks):
            if not self._needs_metadata_refresh(track):
                continue
            path = track.get("path", "")
            if not path or not Path(path).exists():
                continue
            refreshed = self._extractor.extract(path).to_json()
            self._tracks[idx] = refreshed
            changed = True
        return changed

    @staticmethod
    def _needs_metadata_refresh(track: dict) -> bool:
        title_raw = (track.get("title") or "").strip()
        artist_raw = (track.get("artist") or "").strip()
        album_raw = (track.get("album") or "").strip()
        title = title_raw.lower()
        artist = artist_raw.lower()
        album = album_raw.lower()

        has_wrapped = any(
            text.startswith("[") and text.endswith("]")
            for text in (title_raw, artist_raw, album_raw)
        )
        return (
            not title
            or artist in {"", "unknown artist"}
            or album in {"", "unknown album"}
            or has_wrapped
        )

    def _iter_audio_files(self, folder: Path) -> Iterable[Path]:
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                yield path

    def add_folder(self, folder: str | Path) -> int:
        root = Path(folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return 0

        if str(root) not in self._folders:
            self._folders.append(str(root))

        existing = {t["path"] for t in self._tracks}
        added = 0
        for file_path in self._iter_audio_files(root):
            if str(file_path) in existing:
                continue
            self._tracks.append(self._extractor.extract(file_path).to_json())
            added += 1

        self._sort_tracks()
        self._write()
        self.library_changed.emit(self.tracks)
        return added

    def add_file(self, audio_file: str | Path) -> bool:
        path = Path(audio_file).expanduser().resolve()
        if (
            not path.exists()
            or not path.is_file()
            or path.suffix.lower() not in AUDIO_EXTENSIONS
        ):
            return False

        if any(t["path"] == str(path) for t in self._tracks):
            return False

        self._tracks.append(self._extractor.extract(path).to_json())
        self._sort_tracks()
        self._write()
        self.library_changed.emit(self.tracks)
        return True

    def remove_folder(self, folder: str | Path) -> int:
        root = Path(folder).expanduser().resolve()
        root_s = str(root)
        if root_s in self._folders:
            self._folders.remove(root_s)

        before = len(self._tracks)
        kept: list[dict] = []
        for track in self._tracks:
            t_path = Path(track.get("path", ""))
            try:
                t_path.relative_to(root)
                continue
            except Exception:
                kept.append(track)
        self._tracks = kept
        removed = before - len(self._tracks)
        self._sort_tracks()
        self._write()
        self.library_changed.emit(self.tracks)
        return removed

    def find_missing_metadata(self) -> list[dict]:
        missing: list[dict] = []
        for track in self._tracks:
            title = (track.get("title") or "").strip().lower()
            artist = (track.get("artist") or "").strip().lower()
            album = (track.get("album") or "").strip().lower()
            if not title or artist in {"", "unknown artist"} or album in {
                "",
                "unknown album",
            }:
                missing.append(track)
        return missing
