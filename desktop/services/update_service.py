from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot

from desktop.services.app_paths import application_directory, resource_path, releases_url, source_root, user_data_directory


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
RELEASE_API_URL = "https://api.github.com/repos/MonnaDang/Web-tool-for-Tuyenn/releases/latest"
RELEASE_ASSET_NAME = "TuyennnToolbox-win64.zip"
RELEASE_CHECKSUM_NAME = f"{RELEASE_ASSET_NAME}.sha256"
USER_AGENT = "TuyennnToolbox-Updater"


@dataclass(slots=True)
class UpdateResult:
    success: bool
    title: str
    detail: str
    restart_required: bool = False
    technical_detail: str = ""
    restart_program: str = ""
    restart_arguments: list[str] = field(default_factory=list)


def _current_version() -> str:
    try:
        data = json.loads(resource_path("version.json").read_text(encoding="utf-8"))
        return str(data["version"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "0.0.0"


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)*", value)
    return tuple(int(part) for part in match.group(0).split(".")) if match else (0,)


def _report(progress_callback: Callable[[int, str], None] | None, value: int, text: str) -> None:
    if progress_callback:
        progress_callback(value, text)


def can_update() -> bool:
    if getattr(sys, "frozen", False):
        return os.name == "nt" and shutil.which("powershell.exe") is not None
    return (source_root() / ".git").is_dir() and shutil.which("git") is not None


def _pull_latest_source(progress_callback: Callable[[int, str], None] | None = None) -> UpdateResult:
    if not can_update():
        return UpdateResult(
            False,
            "Không thể cập nhật tự động",
            f"Hãy tải bản mới từ {releases_url()} rồi giải nén đè lên thư mục ứng dụng cũ.",
        )

    _report(progress_callback, 15, "Đang kiểm tra mã nguồn…")
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
    _report(progress_callback, 100, "Đã kiểm tra xong")
    if "Already up to date" in output:
        return UpdateResult(True, "Ứng dụng đã là bản mới nhất", "Không cần cập nhật thêm lúc này.")
    return UpdateResult(True, "Đã tải bản cập nhật", "Bản mới đã sẵn sàng.", restart_required=True)


def _request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _download_asset(
    url: str,
    destination: Path,
    progress_callback: Callable[[int, str], None] | None,
) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                percent = 15 + round(65 * downloaded / total)
                _report(progress_callback, min(80, percent), "Đang tải bản cập nhật…")


def _asset_checksum(release: dict, asset: dict) -> str:
    digest = str(asset.get("digest") or "")
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()

    checksum_asset = next(
        (item for item in release.get("assets", []) if item.get("name") == RELEASE_CHECKSUM_NAME),
        None,
    )
    if not checksum_asset or not checksum_asset.get("browser_download_url"):
        raise RuntimeError("Bản phát hành không có mã SHA-256 để kiểm tra file cập nhật.")
    request = urllib.request.Request(str(checksum_asset["browser_download_url"]), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        checksum_text = response.read(4096).decode("ascii", errors="replace")
    match = re.search(r"\b[0-9a-fA-F]{64}\b", checksum_text)
    if not match:
        raise RuntimeError("Không đọc được mã SHA-256 của bản cập nhật.")
    return match.group(0).lower()


def _verify_digest(release: dict, asset: dict, archive_path: Path) -> None:
    expected = _asset_checksum(release, asset)
    hasher = hashlib.sha256()
    with archive_path.open("rb") as archive:
        while chunk := archive.read(1024 * 1024):
            hasher.update(chunk)
    if hasher.hexdigest().lower() != expected:
        raise RuntimeError("Mã kiểm tra của bản cập nhật không khớp. File tải về có thể đã bị hỏng.")


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination_root != target and destination_root not in target.parents:
                raise RuntimeError("Gói cập nhật chứa đường dẫn không an toàn.")
        archive.extractall(destination)


def _find_staged_application(extracted: Path) -> Path:
    direct = extracted / "TuyennnToolbox.exe"
    nested = extracted / "TuyennnToolbox" / "TuyennnToolbox.exe"
    if direct.is_file():
        return extracted
    if nested.is_file():
        return nested.parent
    matches = list(extracted.rglob("TuyennnToolbox.exe"))
    if len(matches) == 1:
        return matches[0].parent
    raise RuntimeError("Không tìm thấy ứng dụng trong gói cập nhật.")


def _write_update_helper(update_root: Path) -> Path:
    helper = update_root / "apply-update.ps1"
    helper.write_text(
        """param(
    [Parameter(Mandatory=$true)][string]$SourcePath,
    [Parameter(Mandatory=$true)][string]$TargetPath,
    [Parameter(Mandatory=$true)][string]$ExecutableName,
    [Parameter(Mandatory=$true)][int]$RunningProcessId
)
$ErrorActionPreference = 'Stop'
try {
    Wait-Process -Id $RunningProcessId -Timeout 120 -ErrorAction SilentlyContinue
    if (Get-Process -Id $RunningProcessId -ErrorAction SilentlyContinue) {
        throw 'The previous version did not close in time.'
    }
    & robocopy.exe $SourcePath $TargetPath /E /IS /IT /R:3 /W:1 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Could not copy the update files. Robocopy exit code: $LASTEXITCODE"
    }
    Start-Process -FilePath (Join-Path $TargetPath $ExecutableName) -WorkingDirectory $TargetPath
} catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "The update could not be installed.`n`n$($_.Exception.Message)",
        'Tuyennn Toolbox update'
    ) | Out-Null
}
""",
        encoding="utf-8-sig",
    )
    return helper


def _prepare_portable_update(progress_callback: Callable[[int, str], None] | None = None) -> UpdateResult:
    _report(progress_callback, 3, "Đang kiểm tra phiên bản mới…")
    release = _request_json(RELEASE_API_URL)
    latest_version = str(release.get("tag_name") or "").lstrip("vV")
    current_version = _current_version()
    if _version_tuple(latest_version) <= _version_tuple(current_version):
        _report(progress_callback, 100, "Đã kiểm tra xong")
        return UpdateResult(
            True,
            "Ứng dụng đã là bản mới nhất",
            f"Phiên bản {current_version} đang là bản mới nhất.",
        )

    asset = next(
        (item for item in release.get("assets", []) if item.get("name") == RELEASE_ASSET_NAME),
        None,
    )
    if not asset or not asset.get("browser_download_url"):
        return UpdateResult(
            False,
            "Bản cập nhật chưa sẵn sàng",
            f"Phiên bản {latest_version} chưa có gói Windows. Hãy thử lại sau hoặc mở trang bản phát hành.",
        )

    update_root = user_data_directory() / "updates" / f"v{latest_version}"
    if update_root.exists():
        shutil.rmtree(update_root)
    extracted = update_root / "extracted"
    extracted.mkdir(parents=True)
    archive_path = update_root / RELEASE_ASSET_NAME

    _report(progress_callback, 12, f"Đang tải phiên bản {latest_version}…")
    _download_asset(str(asset["browser_download_url"]), archive_path, progress_callback)
    _report(progress_callback, 82, "Đang kiểm tra gói cập nhật…")
    _verify_digest(release, asset, archive_path)
    _report(progress_callback, 88, "Đang chuẩn bị cài đặt…")
    _safe_extract(archive_path, extracted)
    staged_application = _find_staged_application(extracted)
    helper = _write_update_helper(update_root)
    powershell = shutil.which("powershell.exe") or "powershell.exe"
    target = application_directory()
    executable_name = Path(sys.executable).name
    _report(progress_callback, 100, "Bản cập nhật đã sẵn sàng")
    return UpdateResult(
        True,
        f"Sẵn sàng cập nhật lên {latest_version}",
        "Ứng dụng sẽ đóng, thay thế các file chương trình rồi tự mở lại. Tùy chọn cá nhân vẫn được giữ nguyên.",
        restart_required=True,
        restart_program=powershell,
        restart_arguments=[
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(helper),
            "-SourcePath",
            str(staged_application),
            "-TargetPath",
            str(target),
            "-ExecutableName",
            executable_name,
            "-RunningProcessId",
            str(os.getpid()),
        ],
    )


def update_application(progress_callback: Callable[[int, str], None] | None = None) -> UpdateResult:
    try:
        if getattr(sys, "frozen", False):
            return _prepare_portable_update(progress_callback)
        return _pull_latest_source(progress_callback)
    except Exception as error:
        return UpdateResult(
            False,
            "Không thể cập nhật",
            "Không thể chuẩn bị bản cập nhật. Hãy kiểm tra kết nối mạng rồi thử lại.",
            technical_detail=str(error),
        )


class UpdateWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    finished = Signal()

    @Slot()
    def run(self) -> None:
        try:
            self.completed.emit(update_application(self.progress.emit))
        finally:
            self.finished.emit()
