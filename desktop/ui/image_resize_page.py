from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.services.image_resize_service import (
    ImageInfo,
    ImageResizeWorker,
    ResizeConfig,
    ResizeResult,
    estimate_output_size,
    probe_image,
    suggested_target_edge,
    target_dimensions,
)
from desktop.services.settings_service import SettingsService


def format_bytes(value: int) -> str:
    size = float(value)
    units = ["B", "KB", "MB", "GB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.{2 if index >= 2 else 0}f} {units[index]}"


class ImageDropArea(QFrame):
    files_selected = Signal(list)
    browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(170)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignCenter)

        symbol = QLabel("▧")
        symbol.setAlignment(Qt.AlignCenter)
        symbol.setStyleSheet(
            "font-size:28px; color:#5de2c7; background:#0d2c35; border:1px solid #1c5056; border-radius:15px;"
            "min-width:58px; max-width:58px; min-height:58px; max-height:58px;"
        )
        title = QLabel("Kéo nhiều ảnh vào đây")
        title.setObjectName("SectionTitle")
        detail = QLabel("JPG, PNG, WebP, BMP và các định dạng Qt hỗ trợ")
        detail.setObjectName("Muted")
        choose = QPushButton("Chọn nhiều ảnh")
        choose.setObjectName("SecondaryButton")
        choose.clicked.connect(self.browse_requested)
        layout.addWidget(symbol, 0, Qt.AlignHCenter)
        layout.addWidget(title, 0, Qt.AlignHCenter)
        layout.addWidget(detail, 0, Qt.AlignHCenter)
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
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if files:
            self.files_selected.emit(files)
            event.acceptProposedAction()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.browse_requested.emit()
        super().mousePressEvent(event)


class ImageResizePage(QWidget):
    def __init__(self, settings: SettingsService) -> None:
        super().__init__()
        self.setObjectName("Page")
        self.settings = settings
        self.images: list[ImageInfo] = []
        self.last_result: ResizeResult | None = None
        self.worker: ImageResizeWorker | None = None
        self.worker_thread: QThread | None = None
        self._busy = False
        self._build_ui()
        self._restore_settings()

    @property
    def busy(self) -> bool:
        return self._busy

    @staticmethod
    def _heading(kicker: str, title: str, detail: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)
        kicker_label = QLabel(kicker)
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
        detail_label.setWordWrap(True)
        copy.addWidget(title_label)
        copy.addWidget(detail_label)
        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(copy, 1)
        return layout

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        heading_row = QHBoxLayout()
        heading_row.addLayout(
            self._heading(
                "CÔNG CỤ 02",
                "Thu nhỏ ảnh",
                "Chọn nhiều ảnh và một độ phân giải nhỏ hơn ảnh gốc. Kích thước cùng dung lượng ước tính sẽ hiện trước khi xử lý.",
            ),
            1,
        )
        badge = QLabel("●  XỬ LÝ TRÊN MÁY")
        badge.setObjectName("StatusBadge")
        heading_row.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(heading_row)

        self.workspace = QBoxLayout(QBoxLayout.LeftToRight)
        self.workspace.setSpacing(16)
        self.workspace.addWidget(self._build_files_panel(), 6)
        self.workspace.addWidget(self._build_options_panel(), 5)
        layout.addLayout(self.workspace)
        layout.addWidget(self._build_estimate_panel())
        layout.addWidget(self._build_result_panel())
        layout.addStretch()

    def _build_files_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(23, 22, 23, 23)
        panel_layout.setSpacing(14)
        panel_layout.addLayout(self._panel_header("1", "Chọn ảnh", "Có thể chọn hoặc kéo thả nhiều ảnh cùng lúc."))
        self.drop_area = ImageDropArea()
        self.drop_area.browse_requested.connect(self._choose_images)
        self.drop_area.files_selected.connect(self._add_images)
        panel_layout.addWidget(self.drop_area)

        selected_header = QHBoxLayout()
        self.selected_summary = QLabel("Chưa chọn ảnh")
        self.selected_summary.setObjectName("ResultMeta")
        clear_button = QPushButton("Xóa danh sách")
        clear_button.setObjectName("LinkButton")
        clear_button.clicked.connect(self._clear_images)
        selected_header.addWidget(self.selected_summary, 1)
        selected_header.addWidget(clear_button)
        panel_layout.addLayout(selected_header)
        self.image_list = QTreeWidget()
        self.image_list.setColumnCount(3)
        self.image_list.setHeaderLabels(["Ảnh", "Kích thước", "Dung lượng"])
        self.image_list.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.image_list.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.image_list.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.image_list.setMaximumHeight(150)
        panel_layout.addWidget(self.image_list)
        return panel

    def _build_options_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(23, 22, 23, 23)
        panel_layout.setSpacing(13)
        panel_layout.addLayout(
            self._panel_header(
                "2",
                "Chọn độ phân giải",
                "Cạnh dài nhất sẽ bằng số pixel đã chọn; ảnh không bị kéo méo.",
            )
        )

        self.resolution_group = QButtonGroup(self)
        self.resolution_group.setExclusive(True)
        self.resolution_options: dict[int, QRadioButton] = {}
        preset_row = QHBoxLayout()
        for edge in (1920, 1280, 800, 480):
            option = QRadioButton(f"{edge}px")
            option.toggled.connect(self._refresh_estimates)
            self.resolution_group.addButton(option, edge)
            self.resolution_options[edge] = option
            preset_row.addWidget(option)
        panel_layout.addLayout(preset_row)

        output_label = QLabel("Nơi lưu kết quả")
        output_label.setStyleSheet("font-weight:700;")
        panel_layout.addWidget(output_label)
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        browse = QPushButton("Chọn thư mục")
        browse.setObjectName("SecondaryButton")
        browse.clicked.connect(self._choose_output_folder)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(browse)
        panel_layout.addLayout(output_row)

        action_row = QHBoxLayout()
        self.resize_button = QPushButton("Tạo ảnh đã thu nhỏ  →")
        self.resize_button.setObjectName("PrimaryButton")
        self.resize_button.setEnabled(False)
        self.resize_button.clicked.connect(self._start_resize)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("SecondaryButton")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel)
        action_row.addWidget(self.resize_button, 1)
        action_row.addWidget(self.cancel_button)
        panel_layout.addLayout(action_row)
        panel_layout.addStretch()
        self._refresh_resolution_availability()
        return panel

    def _build_estimate_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ResultPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(21, 18, 21, 20)
        panel_layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("Ước tính trước khi tạo")
        title.setObjectName("SectionTitle")
        self.estimate_summary = QLabel("Chọn ảnh để xem trước")
        self.estimate_summary.setObjectName("ResultMeta")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.estimate_summary)
        panel_layout.addLayout(header)
        self.estimate_tree = QTreeWidget()
        self.estimate_tree.setColumnCount(4)
        self.estimate_tree.setHeaderLabels(["Ảnh", "Bản thu nhỏ", "Kích thước dự kiến", "Dung lượng ước tính"])
        self.estimate_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 4):
            self.estimate_tree.header().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.estimate_tree.setMaximumHeight(190)
        panel_layout.addWidget(self.estimate_tree)
        note = QLabel(
            "Ước tính dựa trên tỷ lệ số điểm ảnh và có thể khác dung lượng thực tế do nội dung và định dạng ảnh. "
            "Mức lớn hơn hoặc bằng ảnh gốc sẽ tự được bỏ qua để không phóng to ảnh."
        )
        note.setObjectName("FieldHint")
        note.setWordWrap(True)
        panel_layout.addWidget(note)
        return panel

    def _build_result_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ResultPanel")
        panel.setVisible(False)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(21, 18, 21, 20)
        panel_layout.setSpacing(10)
        header = QHBoxLayout()
        copy = QVBoxLayout()
        self.result_title = QLabel("Đang chuẩn bị…")
        self.result_title.setObjectName("SectionTitle")
        self.result_meta = QLabel()
        self.result_meta.setObjectName("ResultMeta")
        copy.addWidget(self.result_title)
        copy.addWidget(self.result_meta)
        self.open_folder_button = QPushButton("Mở thư mục kết quả")
        self.open_folder_button.setObjectName("SecondaryButton")
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self._open_output_folder)
        header.addLayout(copy, 1)
        header.addWidget(self.open_folder_button)
        panel_layout.addLayout(header)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        panel_layout.addWidget(self.progress)
        self.result_tree = QTreeWidget()
        self.result_tree.setColumnCount(4)
        self.result_tree.setHeaderLabels(["File kết quả", "Kích thước", "Dung lượng", "Thao tác"])
        self.result_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 4):
            self.result_tree.header().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.result_tree.setVisible(False)
        panel_layout.addWidget(self.result_tree)
        self.result_panel = panel
        return panel

    def _restore_settings(self) -> None:
        output = str(self.settings.value("image/output_parent", ""))
        if output and Path(output).is_dir():
            self.output_path.setText(output)

    def _choose_images(self) -> None:
        initial = str(self.settings.value("image/input_directory", str(Path.home())))
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn ảnh",
            initial,
            "Ảnh (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff);;Tất cả file (*.*)",
        )
        if selected:
            self._add_images(selected)

    def _add_images(self, selected: list[str]) -> None:
        existing = {info.path.casefold() for info in self.images}
        added: list[ImageInfo] = []
        errors: list[str] = []
        for raw_path in selected:
            path = Path(raw_path)
            try:
                resolved = str(path.resolve())
                if resolved.casefold() in existing:
                    continue
                info = probe_image(path)
                added.append(info)
                existing.add(info.path.casefold())
            except (OSError, ValueError) as error:
                errors.append(str(error))
        self.images.extend(added)
        if added:
            self.settings.set_value("image/input_directory", str(Path(added[0].path).parent))
            if not self.output_path.text():
                self.output_path.setText(str(Path(added[0].path).parent))
            self._select_default_resolution()
        self._refresh_resolution_availability()
        self._refresh_image_list()
        self._refresh_estimates()
        if errors:
            QMessageBox.warning(self, "Một số ảnh không thể thêm", "\n".join(errors[:6]))

    def _clear_images(self) -> None:
        if self._busy:
            return
        self.images.clear()
        self._clear_resolution_selection()
        self._refresh_resolution_availability()
        self._refresh_image_list()
        self._refresh_estimates()

    def _refresh_image_list(self) -> None:
        self.image_list.clear()
        for info in self.images:
            self.image_list.addTopLevelItem(
                QTreeWidgetItem([info.name, f"{info.width} × {info.height}", format_bytes(info.size)])
            )
        total = sum(info.size for info in self.images)
        self.selected_summary.setText(
            f"{len(self.images)} ảnh · {format_bytes(total)}" if self.images else "Chưa chọn ảnh"
        )

    def _selected_edges(self) -> list[int]:
        checked = self.resolution_group.checkedId()
        return [checked] if checked > 0 else []

    def _clear_resolution_selection(self) -> None:
        self.resolution_group.setExclusive(False)
        for option in self.resolution_options.values():
            option.setChecked(False)
        self.resolution_group.setExclusive(True)

    def _select_default_resolution(self) -> None:
        self._clear_resolution_selection()
        if not self.images:
            return
        default_edge = suggested_target_edge(self.images)
        if default_edge:
            self.resolution_options[default_edge].setChecked(True)

    def _refresh_resolution_availability(self) -> None:
        smallest_image_edge = min((max(info.width, info.height) for info in self.images), default=0)
        for edge, option in self.resolution_options.items():
            option.setEnabled(not self._busy and edge < smallest_image_edge)

    def _refresh_estimates(self, *_args) -> None:
        self.estimate_tree.clear()
        total_size = 0
        count = 0
        for info in self.images:
            for edge in self._selected_edges():
                dimensions = target_dimensions(info.width, info.height, edge)
                if dimensions is None:
                    continue
                width, height = dimensions
                estimate = estimate_output_size(info, width, height)
                total_size += estimate
                count += 1
                self.estimate_tree.addTopLevelItem(
                    QTreeWidgetItem([info.name, f"{edge}px", f"{width} × {height}", f"≈ {format_bytes(estimate)}"])
                )
        if count:
            self.estimate_summary.setText(f"{count} file kết quả · khoảng {format_bytes(total_size)}")
        elif self.images and self._selected_edges():
            self.estimate_summary.setText("Ảnh đã nhỏ hơn các mức đã chọn")
        else:
            self.estimate_summary.setText("Chọn ảnh và ít nhất một độ phân giải")
        self.resize_button.setEnabled(bool(count) and not self._busy)

    def _choose_output_folder(self) -> None:
        initial = self.output_path.text() or (
            str(Path(self.images[0].path).parent) if self.images else str(Path.home())
        )
        selected = QFileDialog.getExistingDirectory(self, "Chọn nơi lưu kết quả", initial)
        if selected:
            self.output_path.setText(selected)
            self.settings.set_value("image/output_parent", selected)

    def _start_resize(self) -> None:
        if self._busy:
            return
        output_text = self.output_path.text().strip()
        output_parent = Path(output_text)
        if not output_text or not output_parent.is_dir():
            QMessageBox.warning(self, "Chọn nơi lưu kết quả", "Hãy chọn một thư mục đang tồn tại để lưu ảnh.")
            return
        output_parent = output_parent.resolve()
        config = ResizeConfig(
            images=list(self.images),
            output_parent=output_parent,
            target_edges=self._selected_edges(),
        )
        self.settings.set_value("image/output_parent", str(output_parent))
        self._set_busy(True)
        self.last_result = None
        self.result_panel.setVisible(True)
        self.result_tree.clear()
        self.result_tree.setVisible(False)
        self.open_folder_button.setVisible(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.result_title.setText("Đang thu nhỏ ảnh…")
        self.result_meta.setText("Hãy giữ cửa sổ này mở trong lúc xử lý.")

        self.worker_thread = QThread(self)
        self.worker = ImageResizeWorker(config)
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
        self.resize_button.setText("Đang thu nhỏ ảnh…" if busy else "Tạo ảnh đã thu nhỏ  →")
        self.cancel_button.setVisible(busy)
        self.drop_area.setEnabled(not busy)
        self._refresh_resolution_availability()
        self._refresh_estimates()

    def _on_progress(self, value: int, detail: str) -> None:
        self.progress.setValue(value)
        self.result_title.setText(detail)
        self.result_meta.setText(f"Đã hoàn thành {value}%")

    def _on_completed(self, result: ResizeResult) -> None:
        self.last_result = result
        self.progress.setValue(100)
        self.progress.setVisible(False)
        total_size = sum(item.size for item in result.files)
        self.result_title.setText("✓ Ảnh đã thu nhỏ xong")
        self.result_meta.setText(f"{len(result.files)} file · tổng dung lượng {format_bytes(total_size)}")
        self.result_tree.clear()
        for item in result.files:
            row = QTreeWidgetItem([item.name, f"{item.width} × {item.height}", format_bytes(item.size), ""])
            self.result_tree.addTopLevelItem(row)
            button = QPushButton("Mở")
            button.setObjectName("SecondaryButton")
            button.clicked.connect(
                lambda _checked=False, path=item.path: QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            )
            self.result_tree.setItemWidget(row, 3, button)
        self.result_tree.setVisible(True)
        self.result_tree.setMaximumHeight(self.result_tree.header().height() + min(len(result.files), 6) * 48 + 16)
        self.open_folder_button.setVisible(True)

    def _on_failed(self, detail: str) -> None:
        self.progress.setVisible(False)
        self.result_title.setText("Không thể thu nhỏ ảnh")
        self.result_meta.setText(detail)
        QMessageBox.critical(self, "Không thể thu nhỏ ảnh", detail)

    def _on_cancelled(self) -> None:
        self.progress.setVisible(False)
        self.result_title.setText("Đã hủy")
        self.result_meta.setText("Các file chưa hoàn tất đã được dọn đi.")

    def _thread_finished(self) -> None:
        self._set_busy(False)
        self.worker = None
        self.worker_thread = None

    def cancel(self) -> None:
        if self.worker:
            self.result_title.setText("Đang hủy…")
            self.worker.cancel()

    def wait_for_stop(self, milliseconds: int = 5000) -> bool:
        if not self.worker_thread:
            return True
        self.cancel()
        self.worker_thread.quit()
        return self.worker_thread.wait(milliseconds)

    def _open_output_folder(self) -> None:
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_result.output_directory))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        direction = QBoxLayout.TopToBottom if event.size().width() < 820 else QBoxLayout.LeftToRight
        if self.workspace.direction() != direction:
            self.workspace.setDirection(direction)
