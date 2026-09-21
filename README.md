# Web Tool for Tuyenn

A private local web toolbox. The first tool splits large videos into smaller playable MP4 files, keeps every part below a custom size limit, and can remove time from the beginning or end.

## Features

- Master page ready for additional tools
- Drag-and-drop or local file picker
- Custom maximum part size
- Optional beginning and end trims
- Fast, lossless splitting at existing keyframes
- Precise trimming through re-encoding
- Download links for every completed part
- Local-only processing: videos are never uploaded to an internet service

## Run on Windows

1. Double-click `Start Toolbox.bat`.
2. The app opens at <http://127.0.0.1:4173/#video>.
3. Keep the terminal window open while using the app.

Or start it manually:

```powershell
node server.mjs
```

No npm installation is required. Node.js and FFmpeg/FFprobe must be available. The app automatically checks common Shutter Encoder, YoutubeDownloader, GNU Octave, and system PATH locations. You can also set `FFMPEG_PATH` and `FFPROBE_PATH`.

## Output and privacy

Generated parts are stored under `storage/jobs/` and are excluded from Git. The temporary local copy of the selected source video is removed after a successful job. The original video is never changed.

## GitHub hosting note

GitHub hosts this project's source code. GitHub Pages cannot run the Node.js and FFmpeg processing service, so the working video chunker must be started locally or deployed to a server that supports Node.js and FFmpeg.

