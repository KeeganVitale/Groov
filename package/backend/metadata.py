from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
    ".aiff",
    ".alac",
}


@dataclass(slots=True)
class TrackMetadata:
    path: str
    title: str
    artist: str
    album: str
    year: str
    duration: float
    cover_art_path: str
    composer: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class MetadataExtractor:
    """Extract metadata using mutagen when available with filename fallback."""

    def __init__(self) -> None:
        self._mutagen = None
        try:
            import mutagen  # type: ignore

            self._mutagen = mutagen
        except Exception:
            self._mutagen = None

    def extract(self, path: str | Path) -> TrackMetadata:
        file_path = Path(path).expanduser().resolve()
        title = file_path.stem
        artist = "Unknown Artist"
        album = "Unknown Album"
        year = ""
        duration = 0.0
        cover_art_path = ""
        composer = ""

        if self._mutagen is not None:
            try:
                easy = self._mutagen.File(str(file_path), easy=True)
                raw = self._mutagen.File(str(file_path))

                easy_tags = getattr(easy, "tags", None) if easy is not None else None
                raw_tags = getattr(raw, "tags", None) if raw is not None else None

                title = self._first_any(
                    easy_tags,
                    raw_tags,
                    ("title", "TIT2", "©nam"),
                    title,
                )
                artist = self._first_any(
                    easy_tags,
                    raw_tags,
                    ("artist", "albumartist", "TPE1", "TPE2", "©ART", "aART"),
                    artist,
                )
                album = self._first_any(
                    easy_tags,
                    raw_tags,
                    ("album", "TALB", "©alb"),
                    album,
                )
                year = self._first_any(
                    easy_tags,
                    raw_tags,
                    ("date", "year", "originaldate", "TDRC", "TYER", "©day"),
                    year,
                )
                composer = self._first_any(
                    easy_tags,
                    raw_tags,
                    ("composer", "TCOM", "©wrt"),
                    composer,
                )

                if raw is not None and getattr(raw, "info", None) is not None:
                    duration = float(getattr(raw.info, "length", 0.0) or 0.0)
                    cover_art_path = self._extract_cover_to_cache(file_path, raw)
            except Exception:
                pass

        return TrackMetadata(
            path=str(file_path),
            title=title,
            artist=artist,
            album=album,
            year=year,
            duration=duration,
            cover_art_path=cover_art_path,
            composer=composer,
        )

    @staticmethod
    def _first(tags: Any, key: str, fallback: str) -> str:
        if not tags:
            return fallback
        value = tags.get(key)
        if not value:
            return fallback
        if isinstance(value, (list, tuple)):
            first = value[0] if value else fallback
            return MetadataExtractor._as_text(first, fallback)
        return MetadataExtractor._as_text(value, fallback)

    @staticmethod
    def _as_text(value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        if hasattr(value, "text"):
            text = getattr(value, "text", None)
            if isinstance(text, (list, tuple)):
                value = text[0] if text else fallback
            elif text is not None:
                value = text
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                return fallback
        s = str(value).strip()
        # Mutagen/frame stringification can sometimes look like "['value']".
        if (s.startswith("['") and s.endswith("']")) or (s.startswith('["') and s.endswith('"]')):
            s = s[2:-2].strip()
        elif s.startswith("[") and s.endswith("]"):
            s = s[1:-1].strip()
        return s or fallback

    def _first_any(self, easy_tags: Any, raw_tags: Any, keys: tuple[str, ...], fallback: str) -> str:
        for key in keys:
            value = self._find_value(easy_tags, key)
            text = self._as_text(value, "")
            if text:
                return text
            value = self._find_value(raw_tags, key)
            text = self._as_text(value, "")
            if text:
                return text
        return fallback

    @staticmethod
    def _find_value(tags: Any, key: str) -> Any:
        if not tags:
            return None
        try:
            return tags.get(key)
        except Exception:
            return None

    @staticmethod
    def _extract_cover_to_cache(file_path: Path, raw: Any) -> str:
        cache_dir = file_path.parent / ".groov_cache"
        try:
            tags = getattr(raw, "tags", None)
            if tags is None:
                return ""

            image_bytes = None
            mime_ext = "jpg"

            # ID3/APIC
            if hasattr(tags, "values"):
                for value in tags.values():
                    if value.__class__.__name__.startswith("APIC"):
                        image_bytes = getattr(value, "data", None)
                        mime = getattr(value, "mime", "")
                        if "png" in mime:
                            mime_ext = "png"
                        break

            # FLAC pictures
            if image_bytes is None and hasattr(raw, "pictures") and raw.pictures:
                pic = raw.pictures[0]
                image_bytes = getattr(pic, "data", None)
                mime = getattr(pic, "mime", "")
                if "png" in mime:
                    mime_ext = "png"

            # MP4/M4A covr
            if image_bytes is None and hasattr(tags, "get"):
                covr = tags.get("covr")
                if covr:
                    first = covr[0] if isinstance(covr, (list, tuple)) else covr
                    image_bytes = bytes(first)
                    if getattr(first, "imageformat", None) == 14:
                        mime_ext = "png"

            if not image_bytes:
                return ""

            cache_dir.mkdir(parents=True, exist_ok=True)
            out = cache_dir / f"{file_path.stem}_cover.{mime_ext}"
            out.write_bytes(image_bytes)
            return str(out)
        except Exception:
            return ""
