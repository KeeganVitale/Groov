from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class PlaylistsStore(QObject):
    playlists_changed = Signal(dict)

    def __init__(self, data_file: str | Path) -> None:
        super().__init__()
        self._path = Path(data_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self.load()

    @property
    def data(self) -> dict:
        return self._data

    def _default(self) -> dict:
        return {
            "playlists": {},
            "smart": {
                "recently_added": [],
                "top_25_most_played": [],
                "favorites": [],
            },
            "play_counts": {},
        }

    def load(self) -> None:
        if not self._path.exists():
            self._data = self._default()
            self._write()
            return

        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        except Exception:
            self._data = self._default()

        default = self._default()
        for key, value in default.items():
            self._data.setdefault(key, value)
        self._write()

    def _write(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def sync_from_library(self, tracks: list[dict]) -> None:
        ordered = sorted(
            tracks,
            key=lambda t: (Path(t.get("path", "")).stat().st_mtime if Path(t.get("path", "")).exists() else 0),
            reverse=True,
        )
        self._data["smart"]["recently_added"] = [t["path"] for t in ordered[:100]]
        self._refresh_top_25()
        self._write()
        self.playlists_changed.emit(self._data)

    def _refresh_top_25(self) -> None:
        play_counts = self._data.get("play_counts", {})
        ordered = sorted(play_counts.items(), key=lambda x: x[1], reverse=True)
        self._data["smart"]["top_25_most_played"] = [path for path, _ in ordered[:25]]

    def create_playlist(self, name: str) -> bool:
        n = name.strip()
        if not n or n in self._data["playlists"]:
            return False
        self._data["playlists"][n] = []
        self._write()
        self.playlists_changed.emit(self._data)
        return True

    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        nn = new_name.strip()
        if (
            not nn
            or old_name not in self._data["playlists"]
            or nn in self._data["playlists"]
        ):
            return False
        self._data["playlists"][nn] = self._data["playlists"].pop(old_name)
        self._write()
        self.playlists_changed.emit(self._data)
        return True

    def delete_playlist(self, name: str) -> bool:
        if name not in self._data["playlists"]:
            return False
        del self._data["playlists"][name]
        self._write()
        self.playlists_changed.emit(self._data)
        return True

    def set_playlist_tracks(self, name: str, paths: list[str]) -> bool:
        if name not in self._data["playlists"]:
            return False
        self._data["playlists"][name] = paths
        self._write()
        self.playlists_changed.emit(self._data)
        return True

    def append_to_playlist(self, name: str, path: str) -> bool:
        if name not in self._data["playlists"]:
            return False
        if path in self._data["playlists"][name]:
            return False
        self._data["playlists"][name].append(path)
        self._write()
        self.playlists_changed.emit(self._data)
        return True

    def increment_play_count(self, path: str) -> None:
        play_counts = self._data.setdefault("play_counts", {})
        play_counts[path] = int(play_counts.get(path, 0)) + 1
        self._refresh_top_25()
        self._write()
        self.playlists_changed.emit(self._data)

    def toggle_favorite(self, path: str, is_favorite: bool) -> None:
        favorites: list[str] = self._data["smart"].setdefault("favorites", [])
        if is_favorite and path not in favorites:
            favorites.append(path)
        if not is_favorite and path in favorites:
            favorites.remove(path)
        self._write()
        self.playlists_changed.emit(self._data)
