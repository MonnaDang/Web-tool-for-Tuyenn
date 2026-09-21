# FFmpeg runtime

The desktop application looks here first for `ffmpeg.exe`, `ffprobe.exe`, and their required DLLs.

These native binaries are intentionally excluded from normal Git commits because of their size. Local development currently uses the FFmpeg runtime copied from Shutter Encoder. Portable release builds include the complete runtime inside the release archive.

If this directory is empty after cloning, either:

1. copy a matching Windows FFmpeg/FFprobe build into this directory; or
2. install Shutter Encoder, which the application also detects automatically.

FFmpeg is a separate project and is distributed under its applicable LGPL/GPL license and build configuration.
