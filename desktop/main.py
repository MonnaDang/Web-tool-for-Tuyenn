from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Support both `python -m desktop.main` and direct IDE/script execution.
if not __package__:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from desktop.services.app_paths import resource_path, user_data_directory
from desktop.ui.main_window import APP_VERSION, MainWindow


def load_theme(application: QApplication) -> None:
    theme_path = resource_path("theme.qss")
    if theme_path.is_file():
        application.setStyleSheet(theme_path.read_text(encoding="utf-8"))


def install_exception_handler() -> None:
    log_path = user_data_directory() / "crash.log"

    def handle_exception(exception_type, exception, trace) -> None:
        detail = "".join(traceback.format_exception(exception_type, exception, trace))
        log_path.write_text(detail, encoding="utf-8")
        QMessageBox.critical(
            None,
            "Có lỗi xảy ra",
            f"Ứng dụng đã dừng ngoài ý muốn. Báo cáo kỹ thuật được lưu tại:\n{log_path}",
        )

    sys.excepthook = handle_exception


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Hộp công cụ Tuyennn")
    application.setApplicationDisplayName("Hộp công cụ Tuyennn")
    application.setApplicationVersion(APP_VERSION)
    application.setOrganizationName("Tuyennn")
    application.setWindowIcon(QIcon(str(resource_path("app_icon.svg"))))
    load_theme(application)
    install_exception_handler()

    window = MainWindow()
    window.show()

    if "--smoke-test" in sys.argv:
        QTimer.singleShot(800, application.quit)

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
