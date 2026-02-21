# Groov

Groov is an open-source desktop music player built with Python and Qt (PySide6).

It focuses on local library playback with playlists, podcasts, metadata support, and a live spectrum visualizer.

Repository: https://github.com/KeeganVitale/groov

## Features

- Local music library management (folders + files)
- Playlist management, including smart playlists
- Podcast feed subscription and playback
- Real-time spectrum visualization
- Metadata extraction via `mutagen`
- Audio playback with GStreamer backend

## Tech Stack

- Python 3
- PySide6 (Qt for Python)
- GStreamer (via PyGObject on Linux)
- mutagen

## Project Structure

- `package/main.py`: app entrypoint and main window
- `package/backend/`: audio engine, metadata, stores, spectrum processing
- `package/tabs/`: Library, Playlists, Podcasts, Now Playing, etc.
- `package/menu/`: menu actions
- `assets/`: icons and UI assets
- `flatpak/com.keegan.Groov.yaml`: Flatpak manifest
- `flatpak/run-groov.sh`: Flatpak launcher script

## Running From Source

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Notes:
- On Linux, `PyGObject` is typically provided by OS packages rather than `pip`.
- You need GStreamer + common plugins installed on your system for playback.

### 3. Run the app

```bash
python -m package.main
```

## Flatpak

### Build and install locally

```bash
flatpak-builder --user --install --force-clean build-dir flatpak/com.keegan.Groov.yaml
```

### Run

```bash
flatpak run com.keegan.Groov
```

### Useful test commands

Check GI + GStreamer inside the sandbox:

```bash
flatpak run --command=python3 com.keegan.Groov -c "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; Gst.init(None); print('Gst OK')"
```

Inspect plugins:

```bash
flatpak run --command=gst-inspect-1.0 com.keegan.Groov playbin
flatpak run --command=gst-inspect-1.0 com.keegan.Groov spectrum
```

## Troubleshooting

### No audio playback

- Ensure GStreamer is available (source run) or bundled runtime is installed (Flatpak).
- Verify your output device works in other apps.

### Visualizer not updating

- Make sure audio is actively playing.
- Confirm spectrum plugin availability with `gst-inspect-1.0 spectrum`.

### Taskbar icon does not match window

- Ensure desktop metadata is in sync with app ID:
  - `com.keegan.Groov.desktop`
  - `app.setDesktopFileName("com.keegan.Groov")`

### Flatpak warnings about AppStream

- `com.keegan.Groov.metainfo.xml` is included.
- Add homepage URL metadata if you want a fully clean AppStream validation.

## Contributing

Issues and pull requests are welcome.

## License

MIT. See `LICENCE`.

