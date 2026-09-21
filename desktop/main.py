from __future__ import annotations

import sys
import traceback

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
            "Tuyennn Toolbox stopped unexpectedly",
            f"A diagnostic report was saved to:\n{log_path}",
        )

    sys.excepthook = handle_exception


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Tuyennn Toolbox")
    application.setApplicationDisplayName("Tuyennn Toolbox")
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
