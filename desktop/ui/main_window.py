from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QProcess, QPropertyAnimation, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
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
from desktop.ui.image_resize_page import ImageResizePage


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
        raise ValueError("Hãy nhập số giây, MM:SS hoặc HH:MM:SS.") from error
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError("Hãy nhập số giây, MM:SS hoặc HH:MM:SS.")


class DropArea(QFrame):
    file_selected = Signal(str)
    browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(230)
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
        title = QLabel("Kéo video vào đây")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignCenter)
        detail = QLabel("hoặc chọn một file từ máy tính")
        detail.setObjectName("Muted")
        detail.setAlignment(Qt.AlignCenter)
        choose = QPushButton("Chọn video")
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


class SmoothScrollArea(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self._scroll_target = 0
        self._scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._scroll_animation.setDuration(150)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.verticalScrollBar().sliderPressed.connect(self._sync_scroll_target)

    def _sync_scroll_target(self) -> None:
        self._scroll_target = self.verticalScrollBar().value()

    def wheelEvent(self, event) -> None:
        if not event.pixelDelta().isNull():
            super().wheelEvent(event)
            self._sync_scroll_target()
            return

        steps = event.angleDelta().y() / 120
        if not steps:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        if self._scroll_animation.state() != QPropertyAnimation.Running:
            self._scroll_target = bar.value()
        self._scroll_target = max(bar.minimum(), min(bar.maximum(), self._scroll_target - int(steps * 96)))
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(bar.value())
        self._scroll_animation.setEndValue(self._scroll_target)
        self._scroll_animation.start()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = SettingsService()
        self.input_path: Path | None = None
        self.last_result: SplitResult | None = None
        self.worker_thread: QThread | None = None
        self.worker: VideoWorker | None = None
        self._busy = False

        self.setWindowTitle(f"Hộp công cụ Tuyennn {APP_VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("app_icon.svg"))))
        self.resize(1220, 760)
        self.setMinimumSize(960, 660)
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
        brand_subtitle = QLabel("Một góc nhỏ của cậu")
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
        self.overview_nav = self._nav_button("Trang chủ", 0)
        self.video_nav = self._nav_button("Chia video", 1)
        self.image_nav = self._nav_button("Thu nhỏ ảnh", 2)
        self.updates_nav = self._nav_button("Cập nhật", 3)
        sidebar_layout.addWidget(self.overview_nav)
        sidebar_layout.addWidget(self.video_nav)
        sidebar_layout.addWidget(self.image_nav)
        sidebar_layout.addWidget(self.updates_nav)
        sidebar_layout.addStretch()

        status_card = QFrame()
        status_card.setObjectName("UpdateCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(13, 12, 13, 12)
        status_layout.setSpacing(3)
        status_title = QLabel("●  Riêng tư trên máy")
        status_title.setStyleSheet("color:#5de2c7; font-weight:700;")
        self.tool_status = QLabel("Đang chuẩn bị…")
        self.tool_status.setObjectName("BrandSubtitle")
        self.tool_status.setWordWrap(True)
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.tool_status)
        sidebar_layout.addWidget(status_card)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_overview_page())
        self.pages.addWidget(self._scroll_page(self._build_video_page()))
        self.image_page = ImageResizePage(self.settings)
        self.pages.addWidget(self._scroll_page(self.image_page))
        self.pages.addWidget(self._build_updates_page())
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
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(32)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _page_container() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
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
        layout.addLayout(self._heading("GÓC NHỎ CỦA CẬU", "Công cụ gọn nhẹ, dùng ngay trên máy.", "Chuẩn bị ảnh và video riêng tư mà không cần gửi file lên mạng."))
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
        title = QLabel("Chia video")
        title.setObjectName("CardTitle")
        detail = QLabel("Chia video lớn thành các phần dễ gửi, đồng thời có thể bỏ bớt đoạn đầu hoặc cuối.")
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        ready = QLabel("SẴN SÀNG")
        ready.setObjectName("PageKicker")
        copy.addWidget(ready)
        copy.addWidget(title)
        copy.addWidget(detail)
        open_button = QPushButton("Mở công cụ  →")
        open_button.setObjectName("PrimaryButton")
        open_button.clicked.connect(lambda: self._show_page(1))
        card_layout.addWidget(symbol, 0, Qt.AlignTop)
        card_layout.addLayout(copy, 1)
        card_layout.addWidget(open_button, 0, Qt.AlignVCenter)
        layout.addWidget(card)

        image_card = QFrame()
        image_card.setObjectName("ToolCard")
        image_card_layout = QHBoxLayout(image_card)
        image_card_layout.setContentsMargins(26, 26, 26, 26)
        image_card_layout.setSpacing(18)
        image_symbol = QLabel("02")
        image_symbol.setObjectName("StepBadge")
        image_symbol.setAlignment(Qt.AlignCenter)
        image_copy = QVBoxLayout()
        image_copy.setSpacing(6)
        image_ready = QLabel("SẴN SÀNG")
        image_ready.setObjectName("PageKicker")
        image_title = QLabel("Thu nhỏ ảnh")
        image_title.setObjectName("CardTitle")
        image_detail = QLabel("Tạo nhiều độ phân giải cho nhiều ảnh cùng lúc và xem dung lượng ước tính trước khi bắt đầu.")
        image_detail.setObjectName("Muted")
        image_detail.setWordWrap(True)
        image_copy.addWidget(image_ready)
        image_copy.addWidget(image_title)
        image_copy.addWidget(image_detail)
        image_open = QPushButton("Mở công cụ  →")
        image_open.setObjectName("PrimaryButton")
        image_open.clicked.connect(lambda: self._show_page(2))
        image_card_layout.addWidget(image_symbol, 0, Qt.AlignTop)
        image_card_layout.addLayout(image_copy, 1)
        image_card_layout.addWidget(image_open, 0, Qt.AlignVCenter)
        layout.addWidget(image_card)
        layout.addStretch()
        return page

    def _build_video_page(self) -> QWidget:
        page, layout = self._page_container()
        heading_row = QHBoxLayout()
        heading_row.addLayout(self._heading("CÔNG CỤ 01", "Chia video", "Chọn video, đặt dung lượng tối đa và bỏ bớt đoạn đầu hoặc cuối nếu cần."), 1)
        local_badge = QLabel("●  XỬ LÝ TRÊN MÁY")
        local_badge.setObjectName("StatusBadge")
        heading_row.addWidget(local_badge, 0, Qt.AlignTop)
        layout.addLayout(heading_row)

        self.video_workspace = QBoxLayout(QBoxLayout.LeftToRight)
        self.video_workspace.setSpacing(16)
        self.video_workspace.addWidget(self._build_file_panel(), 6)
        self.video_workspace.addWidget(self._build_settings_panel(), 5)
        layout.addLayout(self.video_workspace)
        self.results_panel = self._build_results_panel()
        self.results_panel.setVisible(False)
        layout.addWidget(self.results_panel)
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
        panel_layout.addLayout(self._panel_header("1", "Chọn video", "File gốc luôn được giữ nguyên."))

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
        change = QPushButton("Thay đổi")
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
        panel_layout.addLayout(self._panel_header("2", "Thiết lập các phần", "Mỗi phần nằm dưới giới hạn và tổng cộng không quá năm phần."))

        max_layout, max_hint = self._field_label("Dung lượng tối đa mỗi phần", "Ứng dụng sẽ tự chừa một khoảng an toàn nhỏ.")
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
        start_layout, start_hint = self._field_label("Bỏ bớt đoạn đầu", "HH:MM:SS hoặc số giây")
        self.trim_start = QLineEdit("00:00:00")
        self.trim_start.setPlaceholderText("00:00:00")
        start_layout.addWidget(self.trim_start)
        if start_hint:
            start_layout.addWidget(start_hint)
        end_layout, end_hint = self._field_label("Bỏ bớt đoạn cuối", "HH:MM:SS hoặc số giây")
        self.trim_end = QLineEdit("00:00:00")
        self.trim_end.setPlaceholderText("00:00:00")
        end_layout.addWidget(self.trim_end)
        if end_hint:
            end_layout.addWidget(end_hint)
        trim_row.addLayout(start_layout)
        trim_row.addLayout(end_layout)
        panel_layout.addLayout(trim_row)

        mode_label = QLabel("Cách chia video")
        mode_label.setStyleSheet("font-weight:700;")
        panel_layout.addWidget(mode_label)
        self.fast_mode = QRadioButton("Nhanh — giữ nguyên chất lượng gốc")
        self.precise_mode = QRadioButton("Chính xác — cắt đúng thời điểm đã chọn")
        self.fast_mode.setToolTip("Nhanh hơn, nhưng điểm cắt có thể lệch nhẹ để video vẫn phát tốt.")
        self.precise_mode.setToolTip("Mất nhiều thời gian hơn để điểm cắt chính xác.")
        self.fast_mode.setChecked(True)
        panel_layout.addWidget(self.fast_mode)
        panel_layout.addWidget(self.precise_mode)

        output_layout, output_hint = self._field_label("Nơi lưu kết quả", "Một thư mục mới sẽ được tạo để giữ các phần video.")
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        browse_output = QPushButton("Chọn thư mục")
        browse_output.setObjectName("SecondaryButton")
        browse_output.clicked.connect(self._choose_output_folder)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(browse_output)
        output_layout.addLayout(output_row)
        if output_hint:
            output_layout.addWidget(output_hint)
        panel_layout.addLayout(output_layout)

        action_row = QHBoxLayout()
        self.process_button = QPushButton("Chia video  →")
        self.process_button.setObjectName("PrimaryButton")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._start_processing)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("SecondaryButton")
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
        self.result_title = QLabel("Các phần video sẽ xuất hiện ở đây")
        self.result_title.setObjectName("SectionTitle")
        self.result_meta = QLabel("Mỗi kết quả là một video riêng và có thể mở ngay.")
        self.result_meta.setObjectName("ResultMeta")
        result_copy.addWidget(self.result_title)
        result_copy.addWidget(self.result_meta)
        self.open_folder_button = QPushButton("Mở thư mục kết quả")
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
        self.results_tree.setHeaderLabels(["Phần", "Thời lượng", "Dung lượng", "Thao tác"])
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_tree.setMinimumHeight(0)
        self.results_tree.setVisible(False)
        panel_layout.addWidget(self.results_tree)
        return panel

    def _build_updates_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addLayout(self._heading("BẢO TRÌ", "Cập nhật mà không cần gỡ ứng dụng.", "Tùy chọn cá nhân được giữ riêng nên vẫn còn nguyên sau mỗi lần cập nhật."))
        layout.addSpacing(16)

        card = QFrame()
        card.setObjectName("UpdateCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 24)
        card_layout.setSpacing(11)
        title = QLabel(f"Hộp công cụ Tuyennn {APP_VERSION}")
        title.setObjectName("CardTitle")
        detail = QLabel(
            "Nếu nút cập nhật khả dụng, chỉ cần tải bản mới rồi khởi động lại. Với bản gửi qua file ZIP, giải nén bản mới đè lên thư mục ứng dụng cũ. Các tùy chọn đã lưu vẫn được giữ nguyên."
        )
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        button_row = QHBoxLayout()
        self.update_button = QPushButton("Cập nhật ứng dụng")
        self.update_button.setObjectName("PrimaryButton")
        self.update_button.setEnabled(can_update_from_git())
        self.update_button.clicked.connect(self._update_from_git)
        releases_button = QPushButton("Xem bản phát hành")
        releases_button.setObjectName("SecondaryButton")
        releases_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(releases_url())))
        reload_button = QPushButton("Tải lại giao diện")
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
        settings_title = QLabel("Tùy chọn được giữ lại tại")
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
            self.tool_status.setText("Sẵn sàng · không tải file lên mạng")
        except FileNotFoundError:
            self.tool_status.setText("Thiếu công cụ xử lý video")

    def _choose_file(self) -> None:
        initial = str(self.settings.value("video/input_directory", str(Path.home())))
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn video",
            initial,
            "Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v);;Tất cả file (*.*)",
        )
        if selected:
            self._set_input_file(selected)

    def _set_input_file(self, selected: str) -> None:
        path = Path(selected)
        if not path.is_file():
            QMessageBox.warning(self, "Không tìm thấy video", "Video đã chọn không còn ở vị trí cũ. Hãy chọn lại một file khác.")
            return
        self.input_path = path.resolve()
        self.file_name_label.setText(path.name)
        self.file_details_label.setText(f"{format_bytes(path.stat().st_size)} · sẵn sàng")
        self.drop_area.setVisible(False)
        self.selected_file.setVisible(True)
        self.process_button.setEnabled(not self._busy)
        self.settings.set_value("video/input_directory", str(path.parent))
        if not self.output_path.text():
            self.output_path.setText(str(path.parent))
        self.result_title.setText("Các phần video sẽ xuất hiện ở đây")
        self.result_meta.setText("Mỗi kết quả là một video riêng và có thể mở ngay.")
        self.results_panel.setVisible(False)

    def _choose_output_folder(self) -> None:
        initial = self.output_path.text() or str(self.input_path.parent if self.input_path else Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Chọn nơi lưu kết quả", initial)
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
                raise ValueError("Thời gian bỏ bớt không thể là số âm.")
        except ValueError as error:
            QMessageBox.warning(self, "Kiểm tra thời gian", str(error))
            return

        output_parent = Path(self.output_path.text())
        if not output_parent.is_dir():
            QMessageBox.warning(self, "Chọn nơi lưu kết quả", "Hãy chọn một thư mục đang tồn tại để lưu các phần video.")
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
        self.results_panel.setVisible(True)
        self.results_tree.clear()
        self.results_tree.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.result_title.setText("Đang chuẩn bị…")
        self.result_meta.setText("Ứng dụng đang đọc video và chuẩn bị các phần phù hợp.")

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
        self.process_button.setText("Đang chia video…" if busy else "Chia video  →")
        self.cancel_button.setVisible(busy)

    def _on_progress(self, value: int, text: str) -> None:
        self.progress.setValue(max(self.progress.value(), value))
        self.result_title.setText(self._friendly_progress(text))
        self.result_meta.setText(f"Đã hoàn thành {self.progress.value()}% · hãy giữ cửa sổ này mở")

    @staticmethod
    def _friendly_progress(detail: str) -> str:
        if detail.startswith("Reading video"):
            return "Đang đọc video…"
        if detail.startswith("Creating"):
            return "Đang chia video…"
        if detail.startswith("Verifying"):
            return "Sắp xong rồi…"
        if detail.startswith("Video parts"):
            return "Các phần video đã sẵn sàng"
        return "Đang chuẩn bị…"

    @staticmethod
    def _friendly_error(detail: str) -> str:
        lowered = detail.lower()
        if "ffmpeg" in lowered or "ffprobe" in lowered or "video tool" in lowered:
            return "Không thể chuẩn bị công cụ xử lý video.\n\nHãy mở lại ứng dụng rồi thử lần nữa."
        if "readable video stream" in lowered or "does not contain" in lowered:
            return "Không thể mở video này.\n\nHãy chọn một video khác rồi thử lại."
        if "trims remove the whole video" in lowered:
            return "Khoảng thời gian đã chọn làm video không còn nội dung.\n\nHãy giảm phần bỏ ở đầu hoặc cuối."
        if "five-part limit" in lowered or "selected limit" in lowered or "keyframe" in lowered:
            return "Video này không thể chia thành tối đa năm phần với dung lượng đã chọn.\n\nHãy tăng dung lượng mỗi phần, cắt bớt video hoặc chọn cách chia chính xác."
        if "maximum part size" in lowered:
            return "Dung lượng mỗi phần chưa phù hợp.\n\nHãy chọn một giá trị lớn hơn rồi thử lại."
        if "no video parts" in lowered:
            return "Không tạo được phần video nào.\n\nHãy kiểm tra video rồi thử lại."
        return "Không thể chia video này.\n\nHãy kiểm tra file rồi thử lại."

    def _show_error_dialog(self, friendly: str, technical_detail: str) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Critical)
        dialog.setWindowTitle("Có lỗi xảy ra")
        dialog.setText(friendly)
        close_button = dialog.addButton("Đóng", QMessageBox.AcceptRole)
        dialog.setDefaultButton(close_button)
        dialog.setDetailedText(technical_detail)
        for button in dialog.buttons():
            if button is not close_button:
                button.setText("Chi tiết kỹ thuật")
        dialog.exec()

    def _ask_user(self, title: str, detail: str, confirm_text: str) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Question)
        dialog.setWindowTitle(title)
        dialog.setText(detail)
        confirm_button = dialog.addButton(confirm_text, QMessageBox.AcceptRole)
        cancel_button = dialog.addButton("Hủy", QMessageBox.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.exec()
        return dialog.clickedButton() is confirm_button

    def _on_completed(self, result: SplitResult) -> None:
        self.last_result = result
        self.progress.setValue(100)
        self.result_title.setText("✓ Các phần video đã sẵn sàng")
        largest = max(part.size for part in result.parts)
        self.result_meta.setText(
            f"{len(result.parts)} phần · thời lượng {format_duration(result.processed_duration)} · phần lớn nhất {format_bytes(largest)}"
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
            open_button = QPushButton("Mở")
            open_button.setObjectName("SecondaryButton")
            open_button.clicked.connect(lambda _checked=False, file_path=part.path: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)))
            self.results_tree.setItemWidget(item, 3, open_button)
        self.results_tree.setVisible(True)
        self.results_tree.setFixedHeight(self.results_tree.header().height() + len(result.parts) * 48 + 16)
        self.open_folder_button.setVisible(True)

    def _on_failed(self, detail: str) -> None:
        self.progress.setVisible(False)
        friendly = self._friendly_error(detail)
        self.result_title.setText("Không thể chia video")
        self.result_meta.setText(friendly.replace("\n\n", " "))
        self._show_error_dialog(friendly, detail)

    def _on_cancelled(self) -> None:
        self.progress.setVisible(False)
        self.result_title.setText("Đã hủy")
        self.result_meta.setText("Các file chưa hoàn tất đã được dọn đi.")

    def _thread_finished(self) -> None:
        self._set_busy(False)
        self.worker = None
        self.worker_thread = None

    def _cancel_processing(self) -> None:
        if self.worker:
            self.result_title.setText("Đang hủy…")
            self.worker.cancel()

    def _open_output_folder(self) -> None:
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_result.output_directory))

    def _reload_theme(self) -> None:
        try:
            theme = resource_path("theme.qss").read_text(encoding="utf-8")
            QApplication.instance().setStyleSheet(theme)
            QMessageBox.information(self, "Đã tải lại giao diện", "Giao diện mới đã được áp dụng mà không cần cài lại ứng dụng.")
        except OSError:
            QMessageBox.warning(self, "Không thể tải lại giao diện", "Hãy kiểm tra file giao diện rồi thử lại.")

    def _update_from_git(self) -> None:
        self.update_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = pull_latest_source()
        finally:
            QApplication.restoreOverrideCursor()
            self.update_button.setEnabled(can_update_from_git())
        if not result.success:
            if result.technical_detail:
                self._show_error_dialog(result.detail, result.technical_detail)
            else:
                QMessageBox.warning(self, result.title, result.detail)
            return
        if result.restart_required:
            if self._ask_user(result.title, f"{result.detail}\n\nKhởi động lại ngay để dùng giao diện mới?", "Khởi động lại"):
                QProcess.startDetached(sys.executable, sys.argv)
                QApplication.quit()
            return
        QMessageBox.information(self, result.title, result.detail)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.image_page.busy:
            should_stop = self._ask_user(
                "Dừng thu nhỏ ảnh?",
                "Ảnh vẫn đang được xử lý. Dừng lại và đóng ứng dụng?",
                "Dừng và đóng",
            )
            if not should_stop:
                event.ignore()
                return
            if not self.image_page.wait_for_stop():
                QMessageBox.warning(self, "Vẫn đang dừng", "Ứng dụng vẫn đang dừng quá trình xử lý ảnh. Hãy chờ một chút rồi đóng lại.")
                event.ignore()
                return
        if self._busy:
            should_stop = self._ask_user(
                "Dừng chia video?",
                "Video vẫn đang được xử lý. Dừng lại và đóng ứng dụng?",
                "Dừng và đóng",
            )
            if not should_stop:
                event.ignore()
                return
            if self.worker:
                self.worker.cancel()
            if self.worker_thread:
                self.worker_thread.quit()
            if self.worker_thread and not self.worker_thread.wait(5000):
                QMessageBox.warning(
                    self,
                    "Vẫn đang dừng",
                    "Ứng dụng vẫn đang dừng quá trình xử lý. Hãy chờ một chút rồi đóng lại.",
                )
                event.ignore()
                return
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "video_workspace"):
            return
        direction = QBoxLayout.TopToBottom if event.size().width() < 1120 else QBoxLayout.LeftToRight
        if self.video_workspace.direction() != direction:
            self.video_workspace.setDirection(direction)
