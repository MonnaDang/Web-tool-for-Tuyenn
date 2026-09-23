# Tuyennn Toolbox

A private Windows desktop toolbox built with Python and PySide6. Image and video processing happens on the computer; files are not uploaded to an online service. The desktop GUI follows the Vietnamese-first **Midnight Mint** design system.

## Project layout

```text
Web-tool-for-Tuyenn/
├── web/                 # Deprecated browser snapshot; no further development
├── desktop/
│   ├── main.py          # PySide6 desktop entry point
│   ├── ui/              # Windows and widgets
│   ├── services/        # FFmpeg, settings, and updater logic
│   └── resources/       # Theme, icon, and version metadata
├── bin/                 # Local FFmpeg runtime (not committed to Git)
├── Start Desktop Toolbox.bat
├── Update Toolbox.bat
└── README.md
```

## Run the Windows desktop app

Double-click `Start Desktop Toolbox.bat`. On its first run, it creates a private Python environment and installs PySide6. Later launches open the app directly.

The video chunker supports:

- drag-and-drop or local file selection;
- a custom maximum size for every output file;
- up to five output videos;
- optional removal from the beginning and/or end;
- fast lossless splitting or precise re-encoding;
- background processing, progress, cancellation, and verified output files.

The image resizer supports:

- selecting or dropping multiple local images;
- creating several downscaled resolutions in one batch while preserving aspect ratio;
- estimating every output dimension and the approximate total size before processing;
- background processing, cancellation, and quick access to completed files.

For development:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r desktop\requirements.txt
.venv\Scripts\python -m desktop.main
```

## Update without uninstalling

This app is portable and does not use a Windows installer.

- In a Git checkout, open **Updates → Update from GitHub**, or double-click `Update Toolbox.bat`, then restart the app.
- For a packaged release, extract the newer release over the existing application folder.
- User preferences live in `%LOCALAPPDATA%\TuyennnToolbox`, outside the program folder, so an update does not remove them.
- `resources/theme.qss` is external in a portable build. It can be replaced and reloaded from the Updates page without rebuilding the app.

## Build a portable Windows release

Place a complete compatible FFmpeg runtime in `bin`, including `ffmpeg.exe`, `ffprobe.exe`, and any DLLs those files require. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File desktop\build_portable.ps1
```

The result is `dist\TuyennnToolbox`. Zip that folder for a GitHub Release. Native FFmpeg binaries are intentionally excluded from Git because GitHub Pages cannot run them and their licenses/builds should be managed explicitly per release.

## Deprecated web version

The former browser version remains under `web/` as an archived snapshot. It receives no new features, interface updates, or routine maintenance. All future work targets the Windows desktop GUI.
