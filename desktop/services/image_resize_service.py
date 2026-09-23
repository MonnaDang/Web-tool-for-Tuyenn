from __future__ import annotations

import re
import shutil
import threading
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QImageReader, QImageWriter


class ImageResizeCancelled(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ImageInfo:
    path: str
    name: str
    size: int
    width: int
    height: int
    image_format: str


@dataclass(slots=True, frozen=True)
class ResizeConfig:
    images: list[ImageInfo]
    output_parent: Path
    target_edges: list[int]


@dataclass(slots=True, frozen=True)
class ResizedImage:
    source_name: str
    name: str
    path: str
    size: int
    width: int
    height: int


@dataclass(slots=True)
class ResizeResult:
    output_directory: str
    files: list[ResizedImage]

    def to_dict(self) -> dict:
        return asdict(self)


def _reader_format(reader: QImageReader, path: Path) -> str:
    detected = bytes(reader.format()).decode("ascii", errors="ignore").lower()
    if detected == "jpeg":
        return "jpg"
    return detected or path.suffix.lower().lstrip(".")


def probe_image(path: Path) -> ImageInfo:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    if not reader.canRead():
        raise ValueError(f"Không thể đọc ảnh {path.name}.")
    size = reader.size()
    if not size.isValid():
        raise ValueError(f"Không thể đọc kích thước của {path.name}.")

    width, height = size.width(), size.height()
    transformation = reader.transformation()
    transformation_value = transformation.value if hasattr(transformation, "value") else int(transformation)
    if int(transformation_value) >= 4:
        width, height = height, width

    image_format = _reader_format(reader, path)
    writable = {bytes(item).decode("ascii", errors="ignore").lower() for item in QImageWriter.supportedImageFormats()}
    if image_format == "jpg":
        supported = "jpeg" in writable or "jpg" in writable
    else:
        supported = image_format in writable
    if not supported:
        raise ValueError(f"Định dạng ảnh {path.suffix or image_format} chưa được hỗ trợ để lưu kết quả.")

    return ImageInfo(
        path=str(path.resolve()),
        name=path.name,
        size=path.stat().st_size,
        width=width,
        height=height,
        image_format=image_format,
    )


def target_dimensions(width: int, height: int, max_edge: int) -> tuple[int, int] | None:
    longest = max(width, height)
    if max_edge <= 0 or max_edge >= longest:
        return None
    ratio = max_edge / longest
    return max(1, round(width * ratio)), max(1, round(height * ratio))


def estimate_output_size(info: ImageInfo, width: int, height: int) -> int:
    pixel_ratio = (width * height) / (info.width * info.height)
    # Pixel count is the most stable preflight signal. The small codec factor reflects
    # the quality used by the writer, while the UI deliberately labels this an estimate.
    codec_factor = 0.84 if info.image_format in {"jpg", "jpeg", "webp"} else 1.0
    return max(1024, round(info.size * pixel_ratio * codec_factor))


def _safe_stem(path: Path) -> str:
    normalized = unicodedata.normalize("NFKD", path.stem)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_name).strip("_")
    return cleaned[:80] or "image"


def _unique_directory(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    candidate = parent / "resized_images"
    suffix = 2
    while candidate.exists():
        candidate = parent / f"resized_images_{suffix}"
        suffix += 1
    candidate.mkdir()
    return candidate


def _unique_file(directory: Path, base_name: str, extension: str) -> Path:
    candidate = directory / f"{base_name}.{extension}"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{base_name}_{suffix}.{extension}"
        suffix += 1
    return candidate


class ImageResizeProcessor:
    def __init__(self) -> None:
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ImageResizeCancelled("Image resizing was cancelled.")

    def resize(self, config: ResizeConfig, progress_callback) -> ResizeResult:
        image_jobs = [
            (info, targets)
            for info in config.images
            if (
                targets := [
                    dimensions
                    for edge in sorted(set(config.target_edges), reverse=True)
                    if (dimensions := target_dimensions(info.width, info.height, edge)) is not None
                ]
            )
        ]
        job_count = sum(len(targets) for _info, targets in image_jobs)
        if not job_count:
            raise RuntimeError("Không có ảnh nào lớn hơn các độ phân giải đã chọn.")

        output_directory = _unique_directory(config.output_parent)
        completed: list[ResizedImage] = []
        try:
            completed_count = 0
            for info, targets in image_jobs:
                self._check_cancelled()
                progress_callback(round(completed_count * 100 / job_count), f"Đang đọc {info.name}…")

                reader = QImageReader(info.path)
                reader.setAutoTransform(True)
                image = reader.read()
                if image.isNull():
                    raise RuntimeError(reader.errorString() or f"Không thể mở {info.name}.")

                for width, height in targets:
                    self._check_cancelled()
                    progress_callback(round(completed_count * 100 / job_count), f"Đang thu nhỏ {info.name}…")
                    resized = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    actual_width, actual_height = resized.width(), resized.height()
                    extension = "jpg" if info.image_format in {"jpg", "jpeg"} else info.image_format
                    base = f"{_safe_stem(Path(info.path))}_{actual_width}x{actual_height}"
                    output_path = _unique_file(output_directory, base, extension)

                    writer_format = b"jpeg" if extension == "jpg" else extension.encode("ascii")
                    writer = QImageWriter(str(output_path), writer_format)
                    if extension in {"jpg", "webp"}:
                        writer.setQuality(88)
                    if not writer.write(resized):
                        raise RuntimeError(writer.errorString() or f"Không thể lưu {output_path.name}.")

                    completed.append(
                        ResizedImage(
                            source_name=info.name,
                            name=output_path.name,
                            path=str(output_path),
                            size=output_path.stat().st_size,
                            width=actual_width,
                            height=actual_height,
                        )
                    )
                    completed_count += 1
                    progress_callback(
                        round(completed_count * 100 / job_count),
                        f"Đã tạo {completed_count}/{job_count} ảnh",
                    )

            return ResizeResult(output_directory=str(output_directory), files=completed)
        except Exception:
            shutil.rmtree(output_directory, ignore_errors=True)
            raise


class ImageResizeWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, config: ResizeConfig) -> None:
        super().__init__()
        self.config = config
        self.processor: ImageResizeProcessor | None = None

    @Slot()
    def run(self) -> None:
        try:
            self.processor = ImageResizeProcessor()
            self.completed.emit(self.processor.resize(self.config, self.progress.emit))
        except ImageResizeCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        if self.processor:
            self.processor.cancel()
