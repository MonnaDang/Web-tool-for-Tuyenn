from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.services.app_paths import releases_url, resource_path
from desktop.services.ffmpeg_service import SplitConfig, SplitResult, VideoWorker, locate_video_tools
from desktop.services.settings_service import SettingsService
from desktop.services.update_service import can_update_from_git, pull_latest_source


try:
    APP_VERSION = str(json.loads(resource_path("version.json").read_text(encoding="utf-8"))["version"])
except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
    APP_VERSION = "development"


def format_bytes(value: int) -> str:
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    precision = 2 if index >= 2 else 0
    return f"{size:.{precision}f} {units[index]}"


def format_duration(seconds: float) -> str:
    rounded = max(0, int(round(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_time(value: str) -> float:
    text = value.strip()
    if not text:
        return 0.0
    try:
        if ":" not in text:
            return float(text)
        parts = [float(part) for part in text.split(":")]
    except ValueError as error:
        raise ValueError("Use seconds, MM:SS, or HH:MM:SS for trim values.") from error
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError("Use seconds, MM:SS, or HH:MM:SS for trim values.")


class DropArea(QFrame):
    file_selected = Signal(str)
    browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(310)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        symbol = QLabel("⇧")
        symbol.setAlignment(Qt.AlignCenter)
        symbol.setStyleSheet(
            "font-size: 30px; color: #5de2c7; background: #0d2c35; border: 1px solid #1c5056; border-radius: 15px;"
            "min-width: 58px; max-width: 58px; min-height: 58px; max-height: 58px;"
        )
        title = QLabel("Drop a video here")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignCenter)
        detail = QLabel("or choose a file from this computer")
        detail.setObjectName("Muted")
        detail.setAlignment(Qt.AlignCenter)
        choose = QPushButton("Choose video")
        choose.setObjectName("SecondaryButton")
        choose.clicked.connect(self.browse_requested)

        layout.addWidget(symbol, 0, Qt.AlignHCenter)
        layout.addSpacing(8)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addSpacing(10)
        layout.addWidget(choose, 0, Qt.AlignHCenter)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
        local_files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if local_files:
            self.file_selected.emit(local_files[0])
            event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.browse_requested.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsService()
        self.input_path: Path | None = None
        self.last_result: SplitResult | None = None
        self.worker_thread: QThread | None = None
        self.worker: VideoWorker | None = None
        self._busy = False

        self.setWindowTitle(f"Tuyennn Toolbox {APP_VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("app_icon.svg"))))
        self.resize(1260, 820)
        self.setMinimumSize(980, 680)
        self._build_ui()
        self._restore_settings()
        self._refresh_tool_status()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(235)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 28, 20, 22)
        sidebar_layout.setSpacing(8)

        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(11)
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap(str(resource_path("app_icon.svg"))).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(0)
        brand_title = QLabel("Tuyennn")
        brand_title.setObjectName("BrandTitle")
        brand_subtitle = QLabel("Desktop toolbox")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_copy.addWidget(brand_title)
        brand_copy.addWidget(brand_subtitle)
        brand_layout.addWidget(icon_label)
        brand_layout.addLayout(brand_copy)
        brand_layout.addStretch()
        sidebar_layout.addLayout(brand_layout)
        sidebar_layout.addSpacing(34)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.overview_nav = self._nav_button("Overview", 0)
        self.video_nav = self._nav_button("Video chunker", 1)
        self.updates_nav = self._nav_button("Updates", 2)
        sidebar_layout.addWidget(self.overview_nav)
        sidebar_layout.addWidget(self.video_nav)
        sidebar_layout.addWidget(self.updates_nav)
        sidebar_layout.addStretch()

        status_card = QFrame()
        status_card.setObjectName("UpdateCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(13, 12, 13, 12)
        status_layout.setSpacing(3)
        status_title = QLabel("●  Private by design")
        status_title.setStyleSheet("color:#5de2c7; font-weight:700;")
        self.tool_status = QLabel("Checking local video tools…")
        self.tool_status.setObjectName("BrandSubtitle")
        self.tool_status.setWordWrap(True)
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.tool_status)
        sidebar_layout.addWidget(status_card)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._scroll_page(self._build_overview_page()))
        self.pages.addWidget(self._scroll_page(self._build_video_page()))
        self.pages.addWidget(self._scroll_page(self._build_updates_page()))
        self.pages.currentChanged.connect(self._sync_navigation)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self._show_page(1)

    def _nav_button(self, text: str, index: int) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda _checked=False, page=index: self._show_page(page))
        self.nav_group.addButton(button, index)
        return button

    @staticmethod
    def _scroll_page(content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _page_container() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 36, 42, 42)
        layout.setSpacing(18)
        return page, layout

    @staticmethod
    def _heading(kicker: str, title: str, detail: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)
        kicker_label = QLabel(kicker.upper())
        kicker_label.setObjectName("PageKicker")
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        detail_label = QLabel(detail)
        detail_label.setObjectName("Muted")
        detail_label.setWordWrap(True)
        detail_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(kicker_label)
        layout.addWidget(title_label)
        layout.addWidget(detail_label)
        return layout

    def _build_overview_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addLayout(self._heading("Local workspace", "Your practical file toolbox.", "Prepare videos privately on this computer without uploading them to an online service."))
        layout.addSpacing(18)

        card = QFrame()
        card.setObjectName("ToolCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(26, 26, 26, 26)
        card_layout.setSpacing(18)
        symbol = QLabel("01")
        symbol.setObjectName("StepBadge")
        symbol.setAlignment(Qt.AlignCenter)
        copy = QVBoxLayout()
        copy.setSpacing(6)
        title = QLabel("Video chunker")
        title.setObjectName("CardTitle")
        detail = QLabel("Split large videos into size-limited playable parts, with optional beginning and end trims.")
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        ready = QLabel("READY TO USE")
        ready.setObjectName("PageKicker")
        copy.addWidget(ready)
        copy.addWidget(title)
        copy.addWidget(detail)
        open_button = QPushButton("Open tool  →")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(lambda: self._show_page(1))
        card_layout.addWidget(symbol, 0, Qt.AlignTop)
        card_layout.addLayout(copy, 1)
        card_layout.addWidget(open_button, 0, Qt.AlignVCenter)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _build_video_page(self) -> QWidget:
        page, layout = self._page_container()
        heading_row = QHBoxLayout()
        heading_row.addLayout(self._heading("Tool 01", "Video chunker", "Choose a video, set the maximum part size, and optionally remove time from either end."), 1)
        local_badge = QLabel("●  LOCAL PROCESSING")
        local_badge.setObjectName("StatusBadge")
        heading_row.addWidget(local_badge, 0, Qt.AlignTop)
        layout.addLayout(heading_row)

        workspace = QHBoxLayout()
        workspace.setSpacing(18)
        workspace.addWidget(self._build_file_panel(), 6)
        workspace.addWidget(self._build_settings_panel(), 5)
        layout.addLayout(workspace)
        layout.addWidget(self._build_results_panel())
        layout.addStretch()
        return page

    @staticmethod
    def _panel_header(step: str, title: str, detail: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        badge = QLabel(step)
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignCenter)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        detail_label = QLabel(detail)
        detail_label.setObjectName("FieldHint")
        copy.addWidget(title_label)
        copy.addWidget(detail_label)
        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(copy, 1)
        return layout

    def _build_file_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(23, 22, 23, 23)
        panel_layout.setSpacing(18)
        panel_layout.addLayout(self._panel_header("1", "Choose a video", "The original file is never modified."))

        self.drop_area = DropArea()
        self.drop_area.browse_requested.connect(self._choose_file)
        self.drop_area.file_selected.connect(self._set_input_file)
        panel_layout.addWidget(self.drop_area, 1)

        self.selected_file = QFrame()
        self.selected_file.setObjectName("SelectedFile")
        self.selected_file.setVisible(False)
        selected_layout = QHBoxLayout(self.selected_file)
        selected_layout.setContentsMargins(16, 14, 16, 14)
        selected_layout.setSpacing(12)
        icon = QLabel("▶")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color:#5de2c7; background:#073027; border-radius:10px; min-width:40px; max-width:40px; min-height:40px; max-height:40px;")
        file_copy = QVBoxLayout()
        file_copy.setSpacing(2)
        self.file_name_label = QLabel()
        self.file_name_label.setStyleSheet("font-weight:700;")
        self.file_details_label = QLabel()
        self.file_details_label.setObjectName("FileDetails")
        file_copy.addWidget(self.file_name_label)
        file_copy.addWidget(self.file_details_label)
        change = QPushButton("Change")
        change.setObjectName("LinkButton")
        change.clicked.connect(self._choose_file)
        selected_layout.addWidget(icon)
        selected_layout.addLayout(file_copy, 1)
        selected_layout.addWidget(change)
        panel_layout.addWidget(self.selected_file)
        return panel

    @staticmethod
    def _field_label(title: str, hint: str | None = None) -> tuple[QVBoxLayout, QLabel | None]:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        label = QLabel(title)
        label.setStyleSheet("font-weight:700;")
        layout.addWidget(label)
        hint_label = None
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("FieldHint")
        return layout, hint_label

    def _build_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(23, 22, 23, 23)
        panel_layout.setSpacing(15)
        panel_layout.addLayout(self._panel_header("2", "Part settings", "Every part stays under your limit, with no more than five parts."))

        max_layout, max_hint = self._field_label("Maximum part size", "A little headroom is applied automatically.")
        self.max_size = QDoubleSpinBox()
        self.max_size.setRange(1, 2048)
        self.max_size.setDecimals(1)
        self.max_size.setSingleStep(0.5)
        self.max_size.setSuffix(" MB")
        self.max_size.setValue(24)
        max_layout.addWidget(self.max_size)
        if max_hint:
            max_layout.addWidget(max_hint)
        panel_layout.addLayout(max_layout)

        trim_row = QHBoxLayout()
        trim_row.setSpacing(12)
        start_layout, start_hint = self._field_label("Remove from beginning", "HH:MM:SS or seconds")
        self.trim_start = QLineEdit("00:00:00")
        self.trim_start.setPlaceholderText("00:00:00")
        start_layout.addWidget(self.trim_start)
        if start_hint:
            start_layout.addWidget(start_hint)
        end_layout, end_hint = self._field_label("Remove from end", "HH:MM:SS or seconds")
        self.trim_end = QLineEdit("00:00:00")
        self.trim_end.setPlaceholderText("00:00:00")
        end_layout.addWidget(self.trim_end)
        if end_hint:
            end_layout.addWidget(end_hint)
        trim_row.addLayout(start_layout)
        trim_row.addLayout(end_layout)
        panel_layout.addLayout(trim_row)

        mode_label = QLabel("Processing mode")
        mode_label.setStyleSheet("font-weight:700;")
        panel_layout.addWidget(mode_label)
        self.fast_mode = QRadioButton("Fast & lossless — keeps original quality")
        self.precise_mode = QRadioButton("Precise trim — re-encodes for exact cuts")
        self.fast_mode.setChecked(True)
        panel_layout.addWidget(self.fast_mode)
        panel_layout.addWidget(self.precise_mode)

        output_layout, output_hint = self._field_label("Output location", "A new uniquely named parts folder is created here.")
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        browse_output = QPushButton("Browse")
        browse_output.setObjectName("SecondaryButton")
        browse_output.clicked.connect(self._choose_output_folder)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(browse_output)
        output_layout.addLayout(output_row)
        if output_hint:
            output_layout.addWidget(output_hint)
        panel_layout.addLayout(output_layout)

        action_row = QHBoxLayout()
        self.process_button = QPushButton("Create video parts  →")
        self.process_button.setObjectName("PrimaryButton")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._start_processing)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel_processing)
        action_row.addWidget(self.process_button, 1)
        action_row.addWidget(self.cancel_button)
        panel_layout.addLayout(action_row)
        return panel

    def _build_results_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ResultPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(21, 18, 21, 20)
        panel_layout.setSpacing(12)

        header = QHBoxLayout()
        result_copy = QVBoxLayout()
        result_copy.setSpacing(2)
        self.result_title = QLabel("Your parts will appear here")
        self.result_title.setObjectName("SectionTitle")
        self.result_meta = QLabel("Each result will be a separate, playable MP4 file.")
        self.result_meta.setObjectName("ResultMeta")
        result_copy.addWidget(self.result_title)
        result_copy.addWidget(self.result_meta)
        self.open_folder_button = QPushButton("Open output folder")
        self.open_folder_button.setObjectName("SecondaryButton")
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        header.addLayout(result_copy, 1)
        header.addWidget(self.open_folder_button)
        panel_layout.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        panel_layout.addWidget(self.progress)

        self.results_tree = QTreeWidget()
        self.results_tree.setColumnCount(4)
        self.results_tree.setHeaderLabels(["Part", "Duration", "Size", "Action"])
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setVisible(False)
        panel_layout.addWidget(self.results_tree)
        return panel

    def _build_updates_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addLayout(self._heading("Maintenance", "Update without uninstalling.", "The app uses a portable folder and stores personal settings separately in Windows Local AppData."))
        layout.addSpacing(16)

        card = QFrame()
        card.setObjectName("UpdateCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 24)
        card_layout.setSpacing(11)
        title = QLabel(f"Tuyennn Toolbox {APP_VERSION}")
        title.setObjectName("CardTitle")
        detail = QLabel(
            "Source checkout: use Update from GitHub, then restart. Portable release: extract the newer archive over the existing application folder. Your saved preferences remain untouched."
        )
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        button_row = QHBoxLayout()
        self.update_button = QPushButton("Update from GitHub")
        self.update_button.setObjectName("PrimaryButton")
        self.update_button.setEnabled(can_update_from_git())
        self.update_button.clicked.connect(self._update_from_git)
        releases_button = QPushButton("Open Releases")
        releases_button.setObjectName("SecondaryButton")
        releases_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(releases_url())))
        reload_button = QPushButton("Reload appearance")
        reload_button.setObjectName("SecondaryButton")
        reload_button.clicked.connect(self._reload_theme)
        button_row.addWidget(self.update_button)
        button_row.addWidget(releases_button)
        button_row.addWidget(reload_button)
        button_row.addStretch()
        card_layout.addWidget(title)
        card_layout.addWidget(detail)
        card_layout.addSpacing(5)
        card_layout.addLayout(button_row)
        layout.addWidget(card)

        settings_card = QFrame()
        settings_card.setObjectName("UpdateCard")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(24, 20, 24, 20)
        settings_title = QLabel("Persistent settings")
        settings_title.setObjectName("SectionTitle")
        settings_path = QLabel(self.settings.path)
        settings_path.setObjectName("Muted")
        settings_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(settings_path)
        layout.addWidget(settings_card)
        layout.addStretch()
        return page

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _sync_navigation(self, index: int) -> None:
        button = self.nav_group.button(index)
        if button:
            button.setChecked(True)

    def _restore_settings(self) -> None:
        self.max_size.setValue(float(self.settings.value("video/max_size_mb", 24)))
        mode = str(self.settings.value("video/mode", "fast"))
        self.precise_mode.setChecked(mode == "precise")
        self.fast_mode.setChecked(mode != "precise")
        output = str(self.settings.value("video/output_parent", ""))
        if output and Path(output).is_dir():
            self.output_path.setText(output)

    def _refresh_tool_status(self) -> None:
        try:
            ffmpeg, ffprobe = locate_video_tools()
            self.tool_status.setText(f"Ready · {ffmpeg.name} + {ffprobe.name}")
        except FileNotFoundError:
            self.tool_status.setText("FFmpeg runtime missing")

    def _choose_file(self) -> None:
        initial = str(self.settings.value("video/input_directory", str(Path.home())))
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a video",
            initial,
            "Video files (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;All files (*.*)",
        )
        if selected:
            self._set_input_file(selected)

    def _set_input_file(self, selected: str) -> None:
        path = Path(selected)
        if not path.is_file():
            QMessageBox.warning(self, "Video not found", "The selected file is no longer available.")
            return
        self.input_path = path.resolve()
        self.file_name_label.setText(path.name)
        self.file_details_label.setText(f"{format_bytes(path.stat().st_size)} · ready to process")
        self.drop_area.setVisible(False)
        self.selected_file.setVisible(True)
        self.process_button.setEnabled(not self._busy)
        self.settings.set_value("video/input_directory", str(path.parent))
        if not self.output_path.text():
            self.output_path.setText(str(path.parent))
        self.result_title.setText("Your parts will appear here")
        self.result_meta.setText("Each result will be a separate, playable MP4 file.")

    def _choose_output_folder(self) -> None:
        initial = self.output_path.text() or str(self.input_path.parent if self.input_path else Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Choose output location", initial)
        if selected:
            self.output_path.setText(selected)
            self.settings.set_value("video/output_parent", selected)

    def _start_processing(self) -> None:
        if self._busy or not self.input_path:
            return
        try:
            trim_start = parse_time(self.trim_start.text())
            trim_end = parse_time(self.trim_end.text())
            if trim_start < 0 or trim_end < 0:
                raise ValueError("Trim values cannot be negative.")
        except ValueError as error:
            QMessageBox.warning(self, "Check trim values", str(error))
            return

        output_parent = Path(self.output_path.text())
        if not output_parent.is_dir():
            QMessageBox.warning(self, "Choose an output location", "Select an existing folder for the finished video parts.")
            return

        mode = "precise" if self.precise_mode.isChecked() else "fast"
        config = SplitConfig(
            input_path=self.input_path,
            output_parent=output_parent,
            max_size_mb=self.max_size.value(),
            trim_start=trim_start,
            trim_end=trim_end,
            mode=mode,
        )
        self.settings.set_value("video/max_size_mb", self.max_size.value())
        self.settings.set_value("video/mode", mode)
        self.settings.set_value("video/output_parent", str(output_parent))

        self._set_busy(True)
        self.last_result = None
        self.results_tree.clear()
        self.results_tree.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.result_title.setText("Preparing video…")
        self.result_meta.setText("Reading the source and calculating safe part boundaries.")

        self.worker_thread = QThread(self)
        self.worker = VideoWorker(config)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self._thread_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.process_button.setEnabled(not busy and self.input_path is not None)
        self.process_button.setText("Working…" if busy else "Create video parts  →")
        self.cancel_button.setVisible(busy)

    def _on_progress(self, value: int, text: str) -> None:
        self.progress.setValue(max(self.progress.value(), value))
        self.result_title.setText(text)
        self.result_meta.setText(f"{self.progress.value()}% complete · keep this window open")

    def _on_completed(self, result: SplitResult) -> None:
        self.last_result = result
        self.progress.setValue(100)
        self.result_title.setText("Video parts are ready")
        largest = max(part.size for part in result.parts)
        self.result_meta.setText(
            f"{len(result.parts)} {'part' if len(result.parts) == 1 else 'parts'} · {format_duration(result.processed_duration)} processed · largest {format_bytes(largest)}"
        )
        self.results_tree.clear()
        for index, part in enumerate(result.parts, start=1):
            item = QTreeWidgetItem(
                [
                    f"{index:02d}  {part.name}",
                    format_duration(part.duration),
                    format_bytes(part.size),
                    "",
                ]
            )
            item.setData(0, Qt.UserRole, part.path)
            self.results_tree.addTopLevelItem(item)
            open_button = QPushButton("Open")
            open_button.setObjectName("SecondaryButton")
            open_button.clicked.connect(lambda _checked=False, file_path=part.path: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)))
            self.results_tree.setItemWidget(item, 3, open_button)
        self.results_tree.setVisible(True)
        self.open_folder_button.setVisible(True)

    def _on_failed(self, detail: str) -> None:
        self.progress.setVisible(False)
        self.result_title.setText("Could not create the parts")
        self.result_meta.setText(detail)
        QMessageBox.critical(self, "Video processing failed", detail)

    def _on_cancelled(self) -> None:
        self.progress.setVisible(False)
        self.result_title.setText("Processing cancelled")
        self.result_meta.setText("No incomplete output folder was kept.")

    def _thread_finished(self) -> None:
        self._set_busy(False)
        self.worker = None
        self.worker_thread = None

    def _cancel_processing(self) -> None:
        if self.worker:
            self.result_title.setText("Cancelling…")
            self.worker.cancel()

    def _open_output_folder(self) -> None:
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_result.output_directory))

    def _reload_theme(self) -> None:
        try:
            theme = resource_path("theme.qss").read_text(encoding="utf-8")
            QApplication.instance().setStyleSheet(theme)
            QMessageBox.information(self, "Appearance reloaded", "The external theme file was applied without reinstalling the app.")
        except OSError as error:
            QMessageBox.warning(self, "Could not reload appearance", str(error))

    def _update_from_git(self) -> None:
        self.update_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = pull_latest_source()
        finally:
            QApplication.restoreOverrideCursor()
            self.update_button.setEnabled(can_update_from_git())
        if not result.success:
            QMessageBox.warning(self, result.title, result.detail)
            return
        if result.restart_required:
            choice = QMessageBox.question(self, result.title, f"{result.detail}\n\nRestart now to apply the updated interface?")
            if choice == QMessageBox.Yes:
                QProcess.startDetached(sys.executable, sys.argv)
                QApplication.quit()
            return
        QMessageBox.information(self, result.title, result.detail)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._busy:
            choice = QMessageBox.question(
                self,
                "Stop processing?",
                "A video is still being processed. Stop it and close the application?",
            )
            if choice != QMessageBox.Yes:
                event.ignore()
                return
            if self.worker:
                self.worker.cancel()
            if self.worker_thread:
                self.worker_thread.quit()
            if self.worker_thread and not self.worker_thread.wait(5000):
                QMessageBox.warning(
                    self,
                    "Still stopping",
                    "The video process is still stopping. Please wait a moment and close the app again.",
                )
                event.ignore()
                return
        event.accept()
