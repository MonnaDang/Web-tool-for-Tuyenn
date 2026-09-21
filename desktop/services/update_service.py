from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from desktop.services.app_paths import releases_url, source_root


CREATE_NO_WINDOW = 0x08000000


@dataclass(slots=True)
class UpdateResult:
    success: bool
    title: str
    detail: str
    restart_required: bool = False
    technical_detail: str = ""


def can_update_from_git() -> bool:
    return (source_root() / ".git").is_dir() and shutil.which("git") is not None


def pull_latest_source() -> UpdateResult:
    if not can_update_from_git():
        return UpdateResult(
            False,
            "Cập nhật bằng bản phát hành",
            f"Hãy tải bản mới từ {releases_url()} rồi giải nén đè lên thư mục ứng dụng cũ. Các tùy chọn đã lưu vẫn được giữ nguyên.",
        )

    process = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=source_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    output = (process.stdout + "\n" + process.stderr).strip()
    if process.returncode != 0:
        return UpdateResult(
            False,
            "Không thể cập nhật",
            "Không thể tải bản mới. Hãy kiểm tra kết nối mạng rồi thử lại.",
            technical_detail=output or "Git stopped without details.",
        )
    if "Already up to date" in output:
        return UpdateResult(True, "Ứng dụng đã là bản mới nhất", "Không cần cập nhật thêm lúc này.")
    return UpdateResult(True, "Đã tải bản cập nhật", "Bản mới đã sẵn sàng.", restart_required=True)
