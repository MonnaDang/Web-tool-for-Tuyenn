from __future__ import annotations

import os
import sys
from pathlib import Path


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return source_root()


def bundled_directory() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle).resolve() if bundle else source_root()


def resource_path(name: str) -> Path:
    candidates = [
        application_directory() / "resources" / name,
        source_root() / "desktop" / "resources" / name,
        bundled_directory() / "resources" / name,
        bundled_directory() / "desktop" / "resources" / name,
    ]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[1])


def binary_directories() -> list[Path]:
    return [
        application_directory() / "bin",
        source_root() / "bin",
        bundled_directory() / "bin",
        bundled_directory() / "desktop" / "bin",
    ]


def user_data_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    directory = base / "TuyennnToolbox"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def repository_url() -> str:
    return "https://github.com/MonnaDang/Web-tool-for-Tuyenn"


def releases_url() -> str:
    return f"{repository_url()}/releases"
