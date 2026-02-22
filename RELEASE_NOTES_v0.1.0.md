# Release Notes

## Groov v0.1.0

Initial public release of Groov, an open-source desktop music player built with Python + Qt.

### Highlights

- Local music library management (folders + files)
- Playlist support, including smart playlists
- Podcast feed subscription and playback
- Real-time spectrum visualizer
- Metadata extraction via `mutagen`
- GStreamer-based audio playback backend
- AppImage packaging workflow for Linux (`x86_64`)
- ARM AppImage build recipe included (`aarch64`, build on ARM host)

### Desktop Integration

- Desktop file and icon integration updated for better taskbar/dock identity
- Added `Pin to Dock` action path:
  - `com.keegan.Groov --pin-to-dock`
- Bundled scalable app icon (`groov.svg`) in AppImage icon theme path

### Packaging Notes

- AppImage ships with:
  - Python runtime
  - `PySide6`, `mutagen`, `pycairo`
  - PyGObject + GStreamer runtime packages
- User data is stored in user-writable directories for sandboxed/read-only bundles (Flatpak/AppImage)
- Bundled sample/user library and playlist data removed from release defaults

### Assets

- `Groov-0.1.0-x86_64.AppImage`
- `sha256sums.txt`
- `Groov-0.1.0-aarch64.AppImage` (if provided for this release)

### Verify Download

```bash
sha256sum -c sha256sums.txt
