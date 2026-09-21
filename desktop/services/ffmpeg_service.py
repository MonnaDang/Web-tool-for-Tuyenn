from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from desktop.services.app_paths import binary_directories


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class ProcessingCancelled(RuntimeError):
    pass


@dataclass(slots=True)
class VideoProbe:
    duration: float
    size: int
    codec: str
    width: int | None
    height: int | None
    has_audio: bool


@dataclass(slots=True)
class SplitConfig:
    input_path: Path
    output_parent: Path
    max_size_mb: float
    trim_start: float
    trim_end: float
    mode: str
    max_parts: int = 5


@dataclass(slots=True)
class PartResult:
    name: str
    path: str
    size: int
    duration: float


@dataclass(slots=True)
class SplitResult:
    output_directory: str
    source: VideoProbe
    processed_duration: float
    mode: str
    max_size_mb: float
    parts: list[PartResult]

    def to_dict(self) -> dict:
        return asdict(self)


def _is_executable(candidate: Path | str | None) -> Path | None:
    if not candidate:
        return None
    candidate_path = Path(candidate)
    if candidate_path.is_file():
        return candidate_path.resolve()
    resolved = shutil.which(str(candidate))
    return Path(resolved).resolve() if resolved else None


def locate_video_tools() -> tuple[Path, Path]:
    ffmpeg_candidates: list[Path | str] = []
    ffprobe_candidates: list[Path | str] = []
    for directory in binary_directories():
        ffmpeg_candidates.append(directory / "ffmpeg.exe")
        ffprobe_candidates.append(directory / "ffprobe.exe")

    ffmpeg_candidates.extend(
        [
            os.environ.get("FFMPEG_PATH", ""),
            Path(r"C:\Program Files\Shutter Encoder\Library\ffmpeg.exe"),
            Path(r"C:\Users\chuon\Downloads\YoutubeDownloader.win-x86\ffmpeg.exe"),
            "ffmpeg",
        ]
    )
    ffprobe_candidates.extend(
        [
            os.environ.get("FFPROBE_PATH", ""),
            Path(r"C:\Program Files\Shutter Encoder\Library\ffprobe.exe"),
            "ffprobe",
        ]
    )

    ffmpeg = next((found for item in ffmpeg_candidates if (found := _is_executable(item))), None)
    ffprobe = next((found for item in ffprobe_candidates if (found := _is_executable(item))), None)
    if not ffmpeg or not ffprobe:
        raise FileNotFoundError(
            "FFmpeg and FFprobe were not found. Put both programs in the bin folder or install Shutter Encoder."
        )
    return ffmpeg, ffprobe


def _run_capture(executable: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [str(executable), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    if process.returncode != 0:
        detail = "\n".join(line for line in process.stderr.splitlines()[-10:] if line.strip())
        raise RuntimeError(detail or "The video tool stopped unexpectedly.")
    return process


def probe_video(ffprobe: Path, file_path: Path) -> VideoProbe:
    process = _run_capture(
        ffprobe,
        [
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(file_path),
        ],
    )
    data = json.loads(process.stdout)
    streams = data.get("streams") or []
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    duration = float((data.get("format") or {}).get("duration") or 0)
    if not video or duration <= 0:
        raise RuntimeError("This file does not contain a readable video stream.")
    return VideoProbe(
        duration=duration,
        size=int((data.get("format") or {}).get("size") or file_path.stat().st_size),
        codec=str(video.get("codec_name") or "unknown"),
        width=int(video["width"]) if video.get("width") else None,
        height=int(video["height"]) if video.get("height") else None,
        has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
    )


def _safe_stem(file_path: Path) -> str:
    normalized = unicodedata.normalize("NFKD", file_path.stem)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_name).strip("_")
    return cleaned[:80] or "video"


def _unique_output_directory(parent: Path, stem: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    base = parent / f"{stem}_parts"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{base.name}_{suffix}"
        suffix += 1
    candidate.mkdir()
    return candidate


class VideoProcessor:
    def __init__(self) -> None:
        self.ffmpeg, self.ffprobe = locate_video_tools()
        self._cancel_event = threading.Event()
        self._process_lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        with self._process_lock:
            process = self._process
        if process and process.poll() is None:
            process.terminate()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ProcessingCancelled("Processing was cancelled.")

    def _run_ffmpeg(
        self,
        arguments: list[str],
        expected_duration: float,
        progress_callback: Callable[[int, str], None],
        floor: int,
        ceiling: int,
    ) -> None:
        command = [
            str(self.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-progress",
            "pipe:1",
            *arguments,
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        with self._process_lock:
            self._process = process

        try:
            assert process.stdout is not None
            for raw_line in process.stdout:
                self._check_cancelled()
                line = raw_line.strip()
                if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                    try:
                        microseconds = int(line.split("=", 1)[1])
                        ratio = min(1.0, max(0.0, microseconds / 1_000_000 / expected_duration))
                        value = floor + int((ceiling - floor) * ratio)
                        progress_callback(value, "Creating video parts…")
                    except ValueError:
                        pass

            stderr = process.stderr.read() if process.stderr else ""
            return_code = process.wait()
            self._check_cancelled()
            if return_code != 0:
                detail = "\n".join(line for line in stderr.splitlines()[-10:] if line.strip())
                raise RuntimeError(detail or "FFmpeg stopped unexpectedly.")
        finally:
            with self._process_lock:
                self._process = None

    def split(self, config: SplitConfig, progress_callback: Callable[[int, str], None]) -> SplitResult:
        self._check_cancelled()
        progress_callback(2, "Reading video information…")
        source_probe = probe_video(self.ffprobe, config.input_path)
        effective_duration = source_probe.duration - config.trim_start - config.trim_end
        if effective_duration <= 0.05:
            raise RuntimeError("The beginning and end trims remove the whole video.")

        max_bytes = int(config.max_size_mb * 1024 * 1024)
        if max_bytes <= 0:
            raise RuntimeError("Maximum part size must be greater than zero.")

        stem = _safe_stem(config.input_path)
        output_directory = _unique_output_directory(config.output_parent, stem)
        source_bytes_per_second = source_probe.size / source_probe.duration
        segment_seconds = min(effective_duration, max(1.0, (max_bytes * 0.78) / source_bytes_per_second))
        last_largest = 0

        try:
            for attempt in range(7):
                self._check_cancelled()
                for existing in output_directory.glob("*.mp4"):
                    existing.unlink()

                pattern = output_directory / f"{stem}_part_%02d.mp4"
                arguments: list[str] = ["-y"]
                if config.mode == "precise" and config.trim_start > 0:
                    arguments.extend(["-ss", str(config.trim_start)])
                arguments.extend(["-i", str(config.input_path)])
                if config.mode == "fast" and config.trim_start > 0:
                    arguments.extend(["-ss", str(config.trim_start)])
                if effective_duration < source_probe.duration - 0.01:
                    arguments.extend(["-t", str(effective_duration)])
                arguments.extend(["-map", "0:v:0", "-map", "0:a?"])

                if config.mode == "precise":
                    arguments.extend(
                        [
                            "-c:v",
                            "libx264",
                            "-preset",
                            "veryfast",
                            "-crf",
                            "20",
                            "-pix_fmt",
                            "yuv420p",
                            "-force_key_frames",
                            f"expr:gte(t,n_forced*{segment_seconds:.3f})",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "128k",
                        ]
                    )
                else:
                    arguments.extend(["-c", "copy"])

                arguments.extend(
                    [
                        "-f",
                        "segment",
                        "-segment_time",
                        f"{segment_seconds:.3f}",
                        "-segment_time_delta",
                        "0.05",
                        "-segment_start_number",
                        "1",
                        "-reset_timestamps",
                        "1",
                        "-avoid_negative_ts",
                        "make_zero",
                        str(pattern),
                    ]
                )

                progress_callback(6, f"Creating parts · pass {attempt + 1}")
                self._run_ffmpeg(arguments, effective_duration, progress_callback, 7, 90)
                part_paths = sorted(output_directory.glob("*.mp4"), key=lambda item: item.name)
                if not part_paths:
                    raise RuntimeError("No video parts were created.")

                last_largest = max(part.stat().st_size for part in part_paths)
                if last_largest < max_bytes and len(part_paths) <= config.max_parts:
                    progress_callback(93, "Verifying completed parts…")
                    part_results: list[PartResult] = []
                    for index, part_path in enumerate(part_paths, start=1):
                        self._check_cancelled()
                        part_probe = probe_video(self.ffprobe, part_path)
                        part_results.append(
                            PartResult(
                                name=part_path.name,
                                path=str(part_path),
                                size=part_path.stat().st_size,
                                duration=part_probe.duration,
                            )
                        )
                        progress_callback(93 + int(6 * index / len(part_paths)), "Verifying completed parts…")
                    progress_callback(100, "Video parts are ready")
                    return SplitResult(
                        output_directory=str(output_directory),
                        source=source_probe,
                        processed_duration=effective_duration,
                        mode=config.mode,
                        max_size_mb=config.max_size_mb,
                        parts=part_results,
                    )

                if len(part_paths) > config.max_parts and last_largest < max_bytes:
                    segment_seconds = min(
                        effective_duration,
                        segment_seconds * (len(part_paths) / config.max_parts) * 1.02,
                    )
                    continue

                if segment_seconds <= 1.01:
                    break
                reduction = min(0.82, (max_bytes / last_largest) * 0.78)
                segment_seconds = max(1.0, segment_seconds * max(0.25, reduction))

            if config.mode == "fast":
                raise RuntimeError(
                    "The video cannot fit within both the selected size and the five-part limit without re-encoding. "
                    "Try Precise trim mode, trim more video, or choose a larger maximum size."
                )
            raise RuntimeError(
                f"Could not keep every part below the selected limit. Largest attempt: {last_largest / 1024 / 1024:.2f} MB."
            )
        except Exception:
            if output_directory.exists():
                shutil.rmtree(output_directory, ignore_errors=True)
            raise


class VideoWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, config: SplitConfig) -> None:
        super().__init__()
        self.config = config
        self.processor: VideoProcessor | None = None

    @Slot()
    def run(self) -> None:
        try:
            self.processor = VideoProcessor()
            result = self.processor.split(self.config, self.progress.emit)
            self.completed.emit(result)
        except ProcessingCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        if self.processor:
            self.processor.cancel()
