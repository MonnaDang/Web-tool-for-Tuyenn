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


def can_update_from_git() -> bool:
    return (source_root() / ".git").is_dir() and shutil.which("git") is not None


def pull_latest_source() -> UpdateResult:
    if not can_update_from_git():
        return UpdateResult(
            False,
            "Portable update available through Releases",
            f"Download the newest portable archive from {releases_url()} and replace the application folder. Your settings remain in Local AppData.",
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
        return UpdateResult(False, "Update could not be applied", output or "Git stopped without details.")
    if "Already up to date" in output:
        return UpdateResult(True, "You already have the latest version", output)
    return UpdateResult(True, "Update downloaded", output, restart_required=True)
