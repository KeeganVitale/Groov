from __future__ import annotations

import ast
import random
import subprocess
import sys
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QDial,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from .backend.audio_engine import AudioEngine
    from .backend.library_store import LibraryStore
    from .backend.lyrics_fetcher import LyricsFetcher
    from .backend.playlists_store import PlaylistsStore
    from .menu.controls_menu import ControlsMenu
    from .menu.file_menu import FileMenu
    from .menu.tools_menu import ToolsMenu
    from .menu.view_menu import ViewMenu
    from .play_bar import PlayBar
    from .tabs.library_tab import LibraryTab
    from .tabs.music_explorer import MusicExplorerTab
    from .tabs.new_tab import NewTabWidget
    from .tabs.now_playing import NowPlayingTab
    from .tabs.playlists import PlaylistsTab
    from .tabs.podcasts import PodcastsTab
except ImportError:
    from backend.audio_engine import AudioEngine
    from backend.library_store import LibraryStore
    from backend.lyrics_fetcher import LyricsFetcher
    from backend.playlists_store import PlaylistsStore
    from menu.controls_menu import ControlsMenu
    from menu.file_menu import FileMenu
    from menu.tools_menu import ToolsMenu
    from menu.view_menu import ViewMenu
    from play_bar import PlayBar
    from tabs.library_tab import LibraryTab
    from tabs.music_explorer import MusicExplorerTab
    from tabs.new_tab import NewTabWidget
    from tabs.now_playing import NowPlayingTab
    from tabs.playlists import PlaylistsTab
    from tabs.podcasts import PodcastsTab


def _resource_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def _app_icon() -> QIcon:
    icon_path = _resource_path("..", "assets", "icons", "groov.svg")
    if icon_path.exists():
        return QIcon(str(icon_path))

    themed = QIcon.fromTheme("com.keegan.Groov")
    if not themed.isNull():
        return themed
    return QIcon()


def _data_dir() -> Path:
    override = os.environ.get("GROOV_DATA_HOME")
    if override:
        return Path(override).expanduser()

    xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    user_data_dir = xdg_data_home / "Groov"

    # Flatpak and AppImage mount app contents read-only; always use user data.
    if os.environ.get("FLATPAK_ID") or os.environ.get("APPIMAGE"):
        return user_data_dir

    bundled = _resource_path("data")
    if bundled.exists() and os.access(bundled, os.W_OK):
        return bundled
    return user_data_dir


class StartupSplash(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(360, 130)
        self.setStyleSheet(
            """
            QDialog {
                background: #f3f4f6;
                border: 1px solid #d7dce3;
                border-radius: 10px;
            }
            QLabel { color: #101217; }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        icon = QLabel()
        icon.setFixedSize(56, 56)
        icon_path = _resource_path("..", "assets", "icons", "groov.svg")
        pix = QIcon(str(icon_path)).pixmap(56, 56)
        if not pix.isNull():
            icon.setPixmap(pix)
        root.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        title = QLabel("Groov")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        tagline = QLabel("The open source music player")
        build = QLabel("Building window 0")

        text_col.addWidget(title)
        text_col.addWidget(tagline)
        text_col.addWidget(build)
        text_col.addStretch(1)
        root.addLayout(text_col, 1)

    def show_centered(self, app: QApplication) -> None:
        screen = app.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.show()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Groov")
        self.resize(1400, 860)
        self.setWindowIcon(_app_icon())

        data_dir = _data_dir()
        self.library_store = LibraryStore(data_dir / "library.json")
        self.playlists_store = PlaylistsStore(data_dir / "playlists.json")
        self.lyrics_fetcher = LyricsFetcher()
        self.audio_engine = AudioEngine()
        self.dynamic_effects_window: QDialog | None = None

        self.current_track: dict | None = None

        self._build_ui()
        self._build_menus()
        self._connect_signals()
        self._show_audio_startup_error_if_any()

        self._sync_library(self.library_store.tracks)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab_request)

        self.library_tab = LibraryTab()
        self.music_explorer_tab = MusicExplorerTab()
        self.now_playing_tab = NowPlayingTab()
        self.playlists_tab = PlaylistsTab()
        self.podcasts_tab = PodcastsTab()
        self.new_tab = NewTabWidget()

        self._tab_order: list[tuple[str, QWidget]] = [
            ("Library", self.library_tab),
            ("Music Explorer", self.music_explorer_tab),
            ("Now Playing", self.now_playing_tab),
            ("Playlists", self.playlists_tab),
            ("Podcasts", self.podcasts_tab),
            ("New Tab", self.new_tab),
        ]
        self._tab_visible = {name: True for name, _ in self._tab_order}
        self._tab_visible["New Tab"] = False
        self._rebuild_tabs()

        self.new_tab_button = QPushButton("+")
        self.new_tab_button.setFixedWidth(28)
        self.new_tab_button.setToolTip("Create New Tab")
        self.new_tab_button.clicked.connect(self._open_new_tab)
        self.tabs.setCornerWidget(self.new_tab_button, Qt.Corner.TopRightCorner)

        self.queue_list = QListWidget()
        self.queue_list.itemDoubleClicked.connect(self._queue_item_double_clicked)
        self.queue_prev = QPushButton("Previous")
        self.queue_next = QPushButton("Next")
        self.queue_prev.clicked.connect(self.audio_engine.previous_track)
        self.queue_next.clicked.connect(self.audio_engine.next_track)

        queue_wrap = QWidget()
        queue_layout = QVBoxLayout(queue_wrap)
        queue_layout.addWidget(QLabel("Now Playing Queue"))
        queue_layout.addWidget(self.queue_list, 1)

        queue_controls = QHBoxLayout()
        queue_controls.addWidget(self.queue_prev)
        queue_controls.addWidget(self.queue_next)
        queue_layout.addLayout(queue_controls)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.tabs)
        split.addWidget(queue_wrap)
        split.setSizes([1100, 300])

        self.play_bar = PlayBar()

        root_layout.addWidget(split, 1)
        root_layout.addWidget(self.play_bar)
        self.setCentralWidget(root)

        # Hide close buttons for non-closeable tabs.
        for idx in range(self.tabs.count()):
            text = self.tabs.tabText(idx)
            if text not in {"Podcasts", "New Tab"}:
                self.tabs.tabBar().setTabButton(idx, self.tabs.tabBar().ButtonPosition.RightSide, None)

        self._build_dsp_sidebar()

    def _build_dsp_sidebar(self) -> None:
        self.dsp_dock = QDockWidget("DSP Effects", self)
        self.dsp_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.dsp_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        close_btn = QPushButton("X")
        close_btn.clicked.connect(self.dsp_dock.hide)
        layout.addWidget(close_btn)

        self.preamp = self._labeled_slider(layout, "Preamp", 0, 200, 100, lambda v: self.audio_engine.set_preamp(v / 100))

        layout.addWidget(QLabel("Equalizer (16-Band)"))
        eq_row = QHBoxLayout()
        eq_row.setSpacing(8)
        self.eq_sliders: list[QSlider] = []
        for i in range(16):
            band_wrap = QWidget()
            band_layout = QVBoxLayout(band_wrap)
            band_layout.setContentsMargins(0, 0, 0, 0)
            band_layout.setSpacing(4)

            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-24, 24)
            slider.setValue(0)
            slider.setTickInterval(6)
            slider.setFixedHeight(140)
            slider.valueChanged.connect(
                lambda v, idx=i: self.audio_engine.set_equalizer_band(idx, float(v))
            )
            band_layout.addWidget(slider, alignment=Qt.AlignmentFlag.AlignHCenter)

            band_label = QLabel(str(i + 1))
            band_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            band_layout.addWidget(band_label)

            eq_row.addWidget(band_wrap)
            self.eq_sliders.append(slider)
        layout.addLayout(eq_row)

        self.bass = self._labeled_slider(layout, "Bass", -24, 24, 0, lambda v: self.audio_engine.set_bass(float(v)))
        self.treble = self._labeled_slider(layout, "Treble", -24, 24, 0, lambda v: self.audio_engine.set_treble(float(v)))
        self.balance = self._labeled_slider(layout, "Balance", -100, 100, 0, lambda v: self.audio_engine.set_balance(v / 100))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        self.dsp_dock.setWidget(scroll)
        self.dsp_dock.setMinimumWidth(560)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dsp_dock)
        self.resizeDocks([self.dsp_dock], [560], Qt.Orientation.Horizontal)
        self.dsp_dock.hide()

    def _build_dynamic_effects_window(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("Dynamic Effects")
        dialog.resize(560, 320)

        layout = QVBoxLayout(dialog)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)

        knobs = [
            ("Limiter", "limiter"),
            ("Compressor", "compressor"),
            ("De-Esser", "de_esser"),
            ("Noise Gate", "noise_gate"),
            ("Expander", "expander"),
        ]
        for col, (label, key) in enumerate(knobs):
            value = int(self.audio_engine.get_dynamic_effect(key) * 100)
            group = QGroupBox(label)
            group_layout = QVBoxLayout(group)
            dial = QDial()
            dial.setRange(0, 100)
            dial.setNotchesVisible(True)
            dial.setValue(value)
            value_label = QLabel(f"{value}%")
            value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            dial.valueChanged.connect(
                lambda v, k=key, out=value_label: (
                    out.setText(f"{v}%"),
                    self.audio_engine.set_dynamic_effect(k, v / 100.0),
                )
            )
            group_layout.addWidget(dial)
            group_layout.addWidget(value_label)
            grid.addWidget(group, 0, col)

        layout.addLayout(grid)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.hide)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return dialog

    def _show_dynamic_effects(self) -> None:
        if self.dynamic_effects_window is None:
            self.dynamic_effects_window = self._build_dynamic_effects_window()
        self.dynamic_effects_window.show()
        self.dynamic_effects_window.raise_()
        self.dynamic_effects_window.activateWindow()

    def _labeled_slider(self, layout: QVBoxLayout, label: str, low: int, high: int, val: int, on_change) -> QSlider:
        layout.addWidget(QLabel(label))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(val)
        slider.valueChanged.connect(on_change)
        layout.addWidget(slider)
        return slider

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()
        self.file_menu = FileMenu(menu_bar)
        self.view_menu = ViewMenu(menu_bar)
        self.controls_menu = ControlsMenu(menu_bar)
        self.tools_menu = ToolsMenu(menu_bar)

    def _connect_signals(self) -> None:
        self.library_store.library_changed.connect(self._sync_library)
        self.audio_engine.track_changed.connect(self._on_track_changed)
        self.audio_engine.position_changed.connect(self._on_position_changed)
        self.audio_engine.state_changed.connect(self._on_state_changed)
        self.audio_engine.queue_changed.connect(self._on_queue_changed)
        self.audio_engine.spectrum_updated.connect(self.play_bar.update_spectrum)
        self.audio_engine.spectrum_updated.connect(self.now_playing_tab.set_spectrum)
        self.audio_engine.error.connect(lambda m: QMessageBox.warning(self, "Audio", m))

        self.library_tab.track_double_clicked.connect(self._play_from_library)
        self.music_explorer_tab.album_play_requested.connect(self._play_album)
        self.playlists_tab.playlist_play_requested.connect(self._play_playlist_paths)
        self.playlists_tab.playlist_rename_requested.connect(self.playlists_store.rename_playlist)
        self.playlists_tab.playlist_delete_requested.connect(self.playlists_store.delete_playlist)
        self.playlists_tab.playlist_add_file_requested.connect(self._add_file_to_playlist)
        self.podcasts_tab.episode_play_requested.connect(
            lambda track, queue: self.audio_engine.play_track(track, queue)
        )
        self.new_tab.podcasts_requested.connect(self._activate_podcasts_from_new_tab)

        self.play_bar.play_pause_clicked.connect(self.audio_engine.toggle_play_pause)
        self.play_bar.previous_clicked.connect(self.audio_engine.previous_track)
        self.play_bar.next_clicked.connect(self.audio_engine.next_track)
        self.play_bar.seek_requested.connect(self.audio_engine.seek)
        self.play_bar.volume_changed.connect(self.audio_engine.set_volume)
        self.now_playing_tab.sample_rate.valueChanged.connect(self._on_sample_rate_changed)

        self.file_menu.add_folder.triggered.connect(self._add_folder)
        self.file_menu.add_file.triggered.connect(self._add_file)
        self.file_menu.remove_folder.triggered.connect(self._remove_folder)
        self.file_menu.stream_url.triggered.connect(self._stream_url)
        self.file_menu.add_playlist.triggered.connect(self._add_playlist)
        self.file_menu.recently_added.triggered.connect(lambda: self._open_smart_playlist("Recently Added"))
        self.file_menu.top_25.triggered.connect(lambda: self._open_smart_playlist("Top 25 Most Played"))
        self.file_menu.favorites.triggered.connect(lambda: self._open_smart_playlist("Favorites"))

        self.view_menu.toggle_library.toggled.connect(lambda v: self._set_tab_visibility("Library", v))
        self.view_menu.toggle_explorer.toggled.connect(lambda v: self._set_tab_visibility("Music Explorer", v))
        self.view_menu.toggle_now_playing.toggled.connect(lambda v: self._set_tab_visibility("Now Playing", v))
        self.view_menu.toggle_playlists.toggled.connect(lambda v: self._set_tab_visibility("Playlists", v))
        self.view_menu.toggle_podcasts.toggled.connect(lambda v: self._set_tab_visibility("Podcasts", v))
        self.view_menu.toggle_spectrum.toggled.connect(self.now_playing_tab.visualizer.setVisible)

        self.controls_menu.dsp_effects.triggered.connect(self.dsp_dock.show)
        self.controls_menu.dynamic_effects.triggered.connect(self._show_dynamic_effects)
        self.controls_menu.repeat.toggled.connect(self.audio_engine.set_repeat)
        self.controls_menu.shuffle.toggled.connect(self.audio_engine.set_shuffle)
        self.controls_menu.stop.triggered.connect(self.audio_engine.stop)
        self.controls_menu.play_pause.triggered.connect(self.audio_engine.toggle_play_pause)
        self.controls_menu.next_track.triggered.connect(self.audio_engine.next_track)

        self.tools_menu.show_missing_metadata.triggered.connect(self._show_missing_metadata)

        self.playlists_store.playlists_changed.connect(self.playlists_tab.set_data)

    def _show_audio_startup_error_if_any(self) -> None:
        if self.audio_engine.startup_error:
            QMessageBox.warning(self, "Audio Backend", self.audio_engine.startup_error)

    def _on_sample_rate_changed(self, value_khz: int) -> None:
        # Map UI slider range (8..48) to a slightly slower visual update rate (8..45 Hz).
        hz = max(8, min(45, int((value_khz / 48.0) * 45)))
        self.audio_engine.set_spectrum_update_rate(hz)
        self.now_playing_tab.set_visualizer_fps(hz)

    def _rebuild_tabs(self) -> None:
        current_name = self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.count() else "Library"
        self.tabs.clear()
        for name, widget in self._tab_order:
            if self._tab_visible.get(name, True):
                self.tabs.addTab(widget, name)

        for idx in range(self.tabs.count()):
            text = self.tabs.tabText(idx)
            if text not in {"Podcasts", "New Tab"}:
                self.tabs.tabBar().setTabButton(idx, self.tabs.tabBar().ButtonPosition.RightSide, None)

        for idx in range(self.tabs.count()):
            if self.tabs.tabText(idx) == current_name:
                self.tabs.setCurrentIndex(idx)
                break

    def _set_tab_visibility(self, name: str, visible: bool) -> None:
        self._tab_visible[name] = visible
        self._rebuild_tabs()

    def _close_tab_request(self, index: int) -> None:
        name = self.tabs.tabText(index)
        if name == "Podcasts":
            self._tab_visible["Podcasts"] = False
            self.view_menu.toggle_podcasts.setChecked(False)
            self._rebuild_tabs()
            return
        if name == "New Tab":
            self._tab_visible["New Tab"] = False
            self._rebuild_tabs()
            return

    def _sync_library(self, tracks: list[dict]) -> None:
        self.library_tab.set_tracks(tracks)
        self.playlists_tab.set_library_tracks(tracks)
        self.music_explorer_tab.set_tracks(tracks, self.playlists_store.data.get("play_counts", {}))
        self.playlists_store.sync_from_library(tracks)
        self.playlists_tab.set_data(self.playlists_store.data)

    def _play_from_library(self, track: dict) -> None:
        queue = self.library_store.tracks
        self.audio_engine.play_track(track, queue)

    def _play_album(self, tracks: list[dict], shuffle: bool) -> None:
        queue = tracks[:]
        if shuffle:
            random.shuffle(queue)
        self.audio_engine.set_queue(queue, 0)

    def _play_playlist_paths(self, paths: list[str], shuffle: bool) -> None:
        tracks_by_path = {t.get("path", ""): t for t in self.library_store.tracks}
        queue = [tracks_by_path[p] for p in paths if p in tracks_by_path]
        if not queue:
            return
        if shuffle:
            random.shuffle(queue)
        self.audio_engine.set_queue(queue, 0)
        self._select_tab("Now Playing")

    def _queue_item_double_clicked(self, item: QListWidgetItem) -> None:
        idx = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(idx, int):
            self.audio_engine.play_index(idx)

    def _on_track_changed(self, track: dict) -> None:
        path = str(track.get("path") or "")
        display_track = dict(track)
        display_track["title"] = str(track.get("title") or (Path(path).stem if path else "Unknown Title"))
        display_track["artist"] = str(track.get("artist") or "Unknown Artist")
        display_track["album"] = str(track.get("album") or "Unknown Album")
        display_track["year"] = str(track.get("year") or "")
        display_track["cover_art_path"] = str(track.get("cover_art_path") or "")

        self.current_track = display_track
        self.play_bar.set_track_info(
            display_track["title"], display_track["artist"], display_track["cover_art_path"]
        )
        self.now_playing_tab.set_track(display_track)
        lyrics = self.lyrics_fetcher.load_for_track(track.get("path", ""))
        self.now_playing_tab.set_lyrics(lyrics)

        if path and not path.startswith(("http://", "https://")):
            self.playlists_store.increment_play_count(path)
            self.music_explorer_tab.set_tracks(self.library_store.tracks, self.playlists_store.data.get("play_counts", {}))

    def _on_position_changed(self, position: float, duration: float) -> None:
        self.play_bar.set_position(position, duration)
        self.now_playing_tab.set_position(position)

    def _on_state_changed(self, state: str) -> None:
        self.play_bar.set_playing(state == "playing")

    def _on_queue_changed(self, queue: list[dict], current_index: int) -> None:
        self.queue_list.clear()
        for idx, track in enumerate(queue):
            path = str(track.get("path") or "")
            title = str(track.get("title") or (Path(path).stem if path else "Unknown Title"))
            artist = str(track.get("artist") or "Unknown Artist")
            label = f"{title}\n{artist}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            cover = str(track.get("cover_art_path") or "")
            if cover and Path(cover).exists():
                item.setIcon(QIcon(QPixmap(cover)))
            self.queue_list.addItem(item)

        if 0 <= current_index < self.queue_list.count():
            self.queue_list.setCurrentRow(current_index)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if folder:
            added = self.library_store.add_folder(folder)
            QMessageBox.information(self, "Library", f"Added {added} tracks.")

    def _add_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Audio File",
            "",
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma *.opus *.aiff *.alac)",
        )
        if path:
            success = self.library_store.add_file(path)
            if not success:
                QMessageBox.information(self, "Library", "File could not be added.")

    def _remove_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Remove Folder")
        if folder:
            removed = self.library_store.remove_folder(folder)
            QMessageBox.information(self, "Library", f"Removed {removed} tracks.")

    def _stream_url(self) -> None:
        url, ok = QInputDialog.getText(self, "Stream URL", "URL:")
        if ok and url.strip():
            self.audio_engine.play_url(url.strip())

    def _add_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Playlist", "Playlist name:")
        if ok and name.strip():
            if not self.playlists_store.create_playlist(name):
                QMessageBox.warning(self, "Playlists", "Playlist exists or name is invalid.")

    def _add_file_to_playlist(self, playlist_name: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Track To Playlist",
            "",
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.wma *.opus *.aiff *.alac)",
        )
        if not path:
            return

        resolved = str(Path(path).expanduser().resolve())
        self.library_store.add_file(resolved)
        if not self.playlists_store.append_to_playlist(playlist_name, resolved):
            QMessageBox.information(
                self,
                "Playlists",
                "Track is already in this playlist or playlist could not be updated.",
            )

    def _open_smart_playlist(self, label: str) -> None:
        self._select_tab("Playlists")
        for i in range(self.playlists_tab.smart_list.count()):
            item = self.playlists_tab.smart_list.item(i)
            if item.text() == label:
                self.playlists_tab.smart_list.setCurrentRow(i)
                break

    def _show_missing_metadata(self) -> None:
        rows = self.library_store.find_missing_metadata()
        if not rows:
            QMessageBox.information(self, "Tagging Tools", "No files with missing metadata found.")
            return

        lines = [f"• {Path(r.get('path', '')).name}" for r in rows[:30]]
        if len(rows) > 30:
            lines.append(f"... and {len(rows) - 30} more")
        QMessageBox.information(self, "Missing Metadata", "\n".join(lines))

    def _activate_podcasts_from_new_tab(self) -> None:
        self._tab_visible["Podcasts"] = True
        self.view_menu.toggle_podcasts.setChecked(True)
        self._rebuild_tabs()
        self._select_tab("Podcasts")

    def _open_new_tab(self) -> None:
        self._tab_visible["New Tab"] = True
        self._rebuild_tabs()
        self._select_tab("New Tab")

    def _select_tab(self, name: str) -> None:
        for idx in range(self.tabs.count()):
            if self.tabs.tabText(idx) == name:
                self.tabs.setCurrentIndex(idx)
                return


def _pin_to_dock() -> int:
    desktop_ids = ["Groov.desktop", "com.keegan.Groov.desktop"]

    try:
        raw = subprocess.check_output(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            text=True,
        ).strip()
    except FileNotFoundError:
        print("gsettings is not available on this system.")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Failed to read GNOME favorites: {exc}")
        return 1

    try:
        favorites = ast.literal_eval(raw)
    except Exception:
        print("Could not parse GNOME favorites list.")
        return 1

    if not isinstance(favorites, list):
        print("Unexpected GNOME favorites format.")
        return 1

    for desktop_id in desktop_ids:
        if desktop_id in favorites:
            print("Groov is already pinned to the dock.")
            return 0

    favorites.append(desktop_ids[0])

    try:
        subprocess.check_call(
            ["gsettings", "set", "org.gnome.shell", "favorite-apps", str(favorites)]
        )
    except subprocess.CalledProcessError as exc:
        print(f"Failed to pin Groov to the dock: {exc}")
        return 1

    print("Groov pinned to dock.")
    return 0


def main() -> int:
    if "--pin-to-dock" in sys.argv[1:]:
        return _pin_to_dock()

    app = QApplication(sys.argv)
    app.setApplicationName("Groov")
    app.setApplicationDisplayName("Groov")
    app.setOrganizationName("keegan")
    app.setDesktopFileName("Groov")
    app.setWindowIcon(_app_icon())

    splash = StartupSplash()
    splash.show_centered(app)
    app.processEvents()

    win = MainWindow()

    def show_main_window() -> None:
        splash.close()
        win.show()
        win.raise_()
        win.activateWindow()

    QTimer.singleShot(2500, show_main_window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
