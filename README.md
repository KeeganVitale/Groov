# Groov

Groov is an open-source desktop music player built with Python and Qt (PySide6).

It focuses on local library playback with playlists, podcasts, metadata support, and a live spectrum visualizer.

Repository: https://github.com/KeeganVitale/Groov

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

## How to Run (AppImage)

1. Download `Groov-0.1.0-x86_64.AppImage`
2. Make it executable:
   ```bash
   chmod +x ./Groov-*.AppImage
3. Go to Groov/ 
4. Right-click `Groov-0.1.0-x86_64.AppImage`
5. Click "Run" 


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

## AppImage

An AppImage recipe is included under `appimage/` and bundles:
- Python runtime
- `PySide6`, `mutagen`, `pycairo` (via pip inside AppDir)
- `PyGObject` + GStreamer + common plugins (via distro packages)

### Build

1. Install `appimage-builder`:

```bash
python3 -m pip install --user appimage-builder
```

2. Build:

```bash
./appimage/build.sh
```

For Raspberry Pi / ARM64 (aarch64), use:

```bash
./appimage/build-aarch64.sh
```

Notes for ARM:
- Build on a 64-bit Raspberry Pi OS/Ubuntu ARM host (`uname -m` should be `aarch64`).
- The ARM recipe is `appimage/AppImageBuilder.aarch64.yml`.

3. The output AppImage will be created in the project root.

### Offline build mode (no internet during build)

If your build machine cannot reach PyPI, pre-download wheels on a machine with internet:

```bash
mkdir -p appimage/wheels
python3 -m pip download --dest appimage/wheels PySide6 mutagen pycairo
```

Then copy `appimage/wheels/` to the build machine and run the normal build command.
The AppImage recipes automatically use local wheels when found in `appimage/wheels`.

### Important notes

- The recipe currently targets Ubuntu `noble` in `appimage/AppImageBuilder.yml`.
  - If your build host is different, update the apt source lines to match your distro codename (for example `jammy`).
- Keep `python3` and `python3-gi` from the same distro repo so GI bindings match the Python ABI.

## Troubleshooting

### No audio playback

- Ensure GStreamer is available (source run) or bundled runtime is installed (Flatpak).
- Verify your output device works in other apps.

### Visualizer not updating

- Make sure audio is actively playing.
- Confirm spectrum plugin availability with `gst-inspect-1.0 spectrum`.

### Taskbar icon does not match window

- Ensure desktop metadata is in sync with app ID:
  - `Groov.desktop`
  - `app.setDesktopFileName("Groov")`

### Flatpak warnings about AppStream

- `com.keegan.Groov.metainfo.xml` is included.
- Add homepage URL metadata if you want a fully clean AppStream validation.

## Publishing on GitHub

Before publishing, run through the release checklist in `RELEASE_CHECKLIST.md`.

Recommended release assets:
- `Groov-<version>-x86_64.AppImage`
- `Groov-<version>-aarch64.AppImage` (if you built on ARM hardware)
- `sha256sums.txt`

Generate checksums:

```bash
sha256sum ./*.AppImage > sha256sums.txt
```

Then create a GitHub Release, attach the AppImage files + `sha256sums.txt`, and include:
- version and date
- major changes
- known limitations (for example AppImage/FUSE notes)

## Contributing

Issues and pull requests are welcome.

## License

MIT. See `LICENCE`.
