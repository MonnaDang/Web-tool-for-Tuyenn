# Web Tool for Tuyennn

A private video toolbox with both a Windows desktop app and the original local web version. Video processing happens on the computer through FFmpeg; files are not uploaded to an online service.

## Project layout

```text
Web-tool-for-Tuyenn/
├── web/                 # Existing browser version
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

## Run the web version

```powershell
cd web
npm start
```

Then open `http://127.0.0.1:4173/#video`. The web version still needs the local Node server because GitHub Pages alone cannot execute FFmpeg on a user's local files.
