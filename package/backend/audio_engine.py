from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from .spectrum import SpectrumAnalyzer


_SPECTRUM_MAG_RE = re.compile(r"magnitude=\(float\)\{([^}]*)\}")

try:
    import gi  # type: ignore

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # type: ignore

    GST_AVAILABLE = True
except Exception:
    Gst = None  # type: ignore
    GST_AVAILABLE = False


class AudioEngine(QObject):
    position_changed = Signal(float, float)
    state_changed = Signal(str)
    track_changed = Signal(dict)
    queue_changed = Signal(list, int)
    spectrum_updated = Signal(list)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._queue: list[dict] = []
        self._current_index: int = -1
        self._shuffle = False
        self._repeat_one = False
        self._volume = 0.75
        self._state = "stopped"

        self._eq_values = [0.0] * 16
        self._bass = 0.0
        self._treble = 0.0
        self._balance = 0.0
        self._preamp = 1.0
        self._dynamic_effects = {
            "limiter": 0.0,
            "compressor": 0.0,
            "de_esser": 0.0,
            "noise_gate": 0.0,
            "expander": 0.0,
        }

        self._spectrum = SpectrumAnalyzer(128)
        self._spectrum.spectrum_ready.connect(self.spectrum_updated.emit)

        self._player = None
        self._eq = None
        self._preamp_elem = None
        self._panorama = None
        self._spectrum_elem = None
        self._startup_error = ""
        self._is_ready = False

        if not GST_AVAILABLE:
            self._startup_error = (
                "GStreamer is not available. Install PyGObject and GStreamer plugins."
            )
            return

        try:
            Gst.init(None)
            self._is_ready = self._build_pipeline()
        except Exception as exc:
            self._startup_error = f"GStreamer init failed: {exc}"
            self._is_ready = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

    @property
    def queue(self) -> list[dict]:
        return list(self._queue)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def startup_error(self) -> str:
        return self._startup_error

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def _build_pipeline(self) -> bool:
        assert Gst is not None
        self._player = Gst.ElementFactory.make("playbin", "player")
        if self._player is None:
            self._startup_error = "Failed to create GStreamer playbin."
            return False

        sink_bin = Gst.Bin.new("audio_chain")
        queue = Gst.ElementFactory.make("queue", "aqueue")
        convert = Gst.ElementFactory.make("audioconvert", "aconvert")
        resample = Gst.ElementFactory.make("audioresample", "aresample")
        self._eq = Gst.ElementFactory.make("equalizer-10bands", "eq")
        self._panorama = Gst.ElementFactory.make("audiopanorama", "pan")
        self._preamp_elem = Gst.ElementFactory.make("volume", "preamp")
        spectrum = Gst.ElementFactory.make("spectrum", "spectrum")
        self._spectrum_elem = spectrum
        sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        elems = [queue, convert, resample, self._eq, self._panorama, self._preamp_elem, spectrum, sink]
        if any(e is None for e in elems) or sink_bin is None:
            self._startup_error = "Missing required GStreamer plugins (equalizer/spectrum/etc)."
            return False

        assert sink_bin is not None
        for element in elems:
            sink_bin.add(element)

        for left, right in zip(elems, elems[1:]):
            if not left.link(right):
                self._startup_error = "Failed to link GStreamer audio elements."
                return False

        pad = queue.get_static_pad("sink")
        ghost = Gst.GhostPad.new("sink", pad)
        if not sink_bin.add_pad(ghost):
            self._startup_error = "Failed to create audio sink ghost pad."
            return False

        spectrum.set_property("bands", 128)
        spectrum.set_property("interval", 20_000_000)
        # Different GStreamer builds expose either "post-messages" or "message".
        prop_names = {p.name for p in spectrum.list_properties()}
        if "post-messages" in prop_names:
            spectrum.set_property("post-messages", True)
        elif "message" in prop_names:
            spectrum.set_property("message", True)

        self._preamp_elem.set_property("volume", self._volume)
        self._panorama.set_property("panorama", 0.0)

        self._player.set_property("audio-sink", sink_bin)
        self._player.set_property("volume", self._volume)

        bus = self._player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)
        self._startup_error = ""
        return True

    def set_queue(self, tracks: list[dict], start_index: int = 0) -> None:
        if not self._is_ready:
            if self._startup_error:
                self.error.emit(self._startup_error)
            return
        self._queue = tracks
        self._current_index = -1
        self.queue_changed.emit(self._queue, self._current_index)
        if not tracks:
            self.stop()
            return
        self.play_index(start_index)

    def play_index(self, index: int) -> None:
        if not self._is_ready:
            if self._startup_error:
                self.error.emit(self._startup_error)
            return
        if not self._queue:
            return
        index = max(0, min(index, len(self._queue) - 1))
        self._current_index = index
        track = self._queue[index]
        self._load_and_play(track)
        self.queue_changed.emit(self._queue, self._current_index)

    def play_track(self, track: dict, queue: list[dict] | None = None) -> None:
        if not self._is_ready:
            if self._startup_error:
                self.error.emit(self._startup_error)
            return
        if queue is None:
            queue = [track]
        self._queue = queue
        self._current_index = queue.index(track) if track in queue else 0
        self._load_and_play(self._queue[self._current_index])
        self.queue_changed.emit(self._queue, self._current_index)

    def _load_and_play(self, track: dict) -> None:
        if not self._is_ready or self._player is None:
            return

        path = track.get("path", "")
        if path.startswith(("http://", "https://")):
            uri = path
        else:
            uri = Path(path).resolve().as_uri()

        self._player.set_state(Gst.State.NULL)
        self._player.set_property("uri", uri)
        self._player.set_state(Gst.State.PLAYING)
        self._state = "playing"
        self.state_changed.emit(self._state)
        self.track_changed.emit(track)

    def play_url(self, url: str) -> None:
        self.play_track(
            {
                "path": url,
                "title": url,
                "artist": "Stream",
                "album": "Internet Radio",
                "year": "",
                "duration": 0.0,
                "cover_art_path": "",
                "composer": "",
            },
            queue=[
                {
                    "path": url,
                    "title": url,
                    "artist": "Stream",
                    "album": "Internet Radio",
                    "year": "",
                    "duration": 0.0,
                    "cover_art_path": "",
                    "composer": "",
                }
            ],
        )

    def play(self) -> None:
        if not self._is_ready or self._player is None:
            return
        self._player.set_state(Gst.State.PLAYING)
        self._state = "playing"
        self.state_changed.emit(self._state)

    def pause(self) -> None:
        if not self._is_ready or self._player is None:
            return
        self._player.set_state(Gst.State.PAUSED)
        self._state = "paused"
        self.state_changed.emit(self._state)

    def toggle_play_pause(self) -> None:
        if self._state == "playing":
            self.pause()
        else:
            if self._current_index < 0 and self._queue:
                self.play_index(0)
            else:
                self.play()

    def stop(self) -> None:
        if not self._is_ready or self._player is None:
            return
        self._player.set_state(Gst.State.NULL)
        self._state = "stopped"
        self.state_changed.emit(self._state)
        self.position_changed.emit(0.0, 0.0)

    def next_track(self) -> None:
        if not self._queue:
            return
        if self._shuffle and len(self._queue) > 1:
            choices = [i for i in range(len(self._queue)) if i != self._current_index]
            self.play_index(random.choice(choices))
            return

        if self._current_index + 1 < len(self._queue):
            self.play_index(self._current_index + 1)
            return

        if self._repeat_one:
            self.play_index(self._current_index)
        else:
            self.stop()

    def previous_track(self) -> None:
        if not self._queue:
            return
        if self._current_index - 1 >= 0:
            self.play_index(self._current_index - 1)
        elif self._repeat_one:
            self.play_index(self._current_index)

    def seek(self, position_seconds: float) -> None:
        if not self._is_ready or self._player is None:
            return
        ns = int(max(position_seconds, 0.0) * Gst.SECOND)
        self._player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, ns)

    def set_volume(self, value_0_1: float) -> None:
        self._volume = max(0.0, min(1.0, value_0_1))
        if self._is_ready and self._player is not None:
            self._player.set_property("volume", self._volume)
        if self._preamp_elem is not None:
            self._preamp_elem.set_property("volume", self._preamp * self._volume)

    def set_repeat(self, enabled: bool) -> None:
        self._repeat_one = enabled

    def set_shuffle(self, enabled: bool) -> None:
        self._shuffle = enabled

    def set_preamp(self, value: float) -> None:
        self._preamp = max(0.0, min(2.0, value))
        if self._preamp_elem is not None:
            self._preamp_elem.set_property("volume", self._preamp * self._volume)

    def set_equalizer_band(self, index: int, gain_db: float) -> None:
        if not 0 <= index < len(self._eq_values):
            return
        self._eq_values[index] = max(-24.0, min(24.0, gain_db))
        self._apply_eq()

    def set_bass(self, value: float) -> None:
        self._bass = max(-24.0, min(24.0, value))
        self._apply_eq()

    def set_treble(self, value: float) -> None:
        self._treble = max(-24.0, min(24.0, value))
        self._apply_eq()

    def set_balance(self, value: float) -> None:
        self._balance = max(-1.0, min(1.0, value))
        if self._panorama is not None:
            self._panorama.set_property("panorama", self._balance)

    def set_spectrum_update_rate(self, hz: int) -> None:
        if self._spectrum_elem is None:
            return
        hz = max(8, min(60, int(hz)))
        interval_ns = int(1_000_000_000 / hz)
        self._spectrum_elem.set_property("interval", interval_ns)

    def set_dynamic_effect(self, effect: str, amount: float) -> None:
        if effect not in self._dynamic_effects:
            return
        self._dynamic_effects[effect] = max(0.0, min(1.0, float(amount)))

    def get_dynamic_effect(self, effect: str) -> float:
        return float(self._dynamic_effects.get(effect, 0.0))

    def _apply_eq(self) -> None:
        if self._eq is None:
            return

        # equalizer-10bands has band0..band9, map 16 virtual bands down to 10.
        mapped = [0.0] * 10
        for i in range(10):
            src_idx = int(i * (len(self._eq_values) - 1) / 9)
            mapped[i] = self._eq_values[src_idx]

        mapped[0] += self._bass * 0.8
        mapped[1] += self._bass * 0.5
        mapped[8] += self._treble * 0.5
        mapped[9] += self._treble * 0.8

        for i, gain in enumerate(mapped):
            self._eq.set_property(f"band{i}", max(-24.0, min(24.0, gain)))

    def _poll(self) -> None:
        if not self._is_ready or self._player is None:
            return

        if self._state in {"playing", "paused"}:
            success_pos, pos = self._player.query_position(Gst.Format.TIME)
            success_dur, dur = self._player.query_duration(Gst.Format.TIME)
            if success_pos and success_dur:
                self.position_changed.emit(pos / Gst.SECOND, max(dur / Gst.SECOND, 0.0))

    def _on_bus_message(self, _bus: Any, msg: Any) -> None:
        self._handle_message(msg)

    def _handle_message(self, msg: Any) -> None:
        if msg.type == Gst.MessageType.EOS:
            self.next_track()
            return

        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            self.error.emit(f"Playback error: {err}; {debug}")
            self.stop()
            return

        if msg.type == Gst.MessageType.ELEMENT:
            structure = msg.get_structure()
            if not structure:
                return
            if structure.get_name() != "spectrum":
                return

            magnitudes = self._extract_magnitudes(structure)
            if magnitudes:
                self._spectrum.update_from_magnitudes(magnitudes)

    @staticmethod
    def _extract_magnitudes(structure: Any) -> list[float]:
        # Most runtimes expose "magnitude" as an iterable value.
        try:
            raw = structure.get_value("magnitude")
            return [float(v) for v in raw]
        except Exception:
            pass

        # GNOME/Flatpak GI can expose GstValueList as an unknown type.
        # Fall back to parsing the serialized structure string.
        try:
            text = structure.to_string()
        except Exception:
            return []

        match = _SPECTRUM_MAG_RE.search(text)
        if not match:
            return []

        values: list[float] = []
        for part in match.group(1).split(","):
            p = part.strip()
            if not p:
                continue
            try:
                values.append(float(p))
            except ValueError:
                continue
        return values
