# Groov Release Checklist

## 1. Preflight

- [ ] Run from source and verify startup:
  - `python -m package.main`
- [ ] Confirm app opens with correct name/icon in taskbar/dock.
- [ ] Confirm no personal data is bundled:
  - `package/data/library.json` should have empty folders/tracks.
  - `package/data/playlists.json` should have empty playlists/play counts.
- [ ] Confirm desktop metadata is aligned:
  - `com.keegan.Groov.desktop`
  - `com.keegan.Groov.metainfo.xml`
  - `app.setDesktopFileName("com.keegan.Groov.desktop")`

## 2. Build Artifacts

- [ ] Build x86_64 AppImage:
  - `./appimage/build.sh`
- [ ] (Optional) Build aarch64 AppImage on ARM host:
  - `./appimage/build-aarch64.sh`
- [ ] Verify produced files exist:
  - `ls -lh *.AppImage`

## 3. Smoke Test Artifacts

- [ ] Launch x86_64 AppImage on a real desktop session.
- [ ] Verify:
  - startup succeeds
  - audio playback works
  - icon and app name display correctly
  - pin-to-dock flow works (`--pin-to-dock` on GNOME)
- [ ] Launch aarch64 artifact on Raspberry Pi (if provided).

## 4. Checksums

- [ ] Generate SHA256 sums:
  - `sha256sum ./*.AppImage > sha256sums.txt`
- [ ] Verify checksum file:
  - `cat sha256sums.txt`

## 5. GitHub Release

- [ ] Create/update release tag (example `v0.1.0`).
- [ ] Create GitHub Release notes including:
  - key features/fixes
  - supported architectures
  - install/run instructions
  - known limitations (FUSE/AppImage behavior, desktop integration notes)
- [ ] Upload assets:
  - `Groov-<version>-x86_64.AppImage`
  - `Groov-<version>-aarch64.AppImage` (if available)
  - `sha256sums.txt`

## 6. Post-Release

- [ ] Download each uploaded asset once and verify checksum.
- [ ] Open a clean issue template for bug reports (optional but recommended).
- [ ] Announce release and include direct release URL.
