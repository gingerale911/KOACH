"""Live Session screen — UI documentation §2.3.

Displays live telemetry status and incoming completed laps during an F1 25 session.
Allows drivers to monitor telemetry recording, view real-time speed, throttle, gear, and RPM,
and directly click any completed lap to jump into full telemetry analysis.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.f125_udp.telemetry_receiver import TelemetryReceiver
from f1_coach.presentation import theme as theme_module
from f1_coach.presentation.theme_manager import ThemeManager

logger = get_logger(__name__)

_TICK_INTERVAL_MS = 250
_STALE_THRESHOLD_SECONDS = 5.0


def _make_stat_chip(icon: str, label: str, color: str) -> tuple[QFrame, QLabel]:
    """Live telemetry chip for speed, gear, throttle, RPM."""
    chip = QFrame()
    chip.setStyleSheet(
        f"QFrame {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
        "  border-radius: 10px; }"
    )
    layout = QHBoxLayout(chip)
    layout.setContentsMargins(10, 6, 12, 6)
    layout.setSpacing(6)

    icon_box = QLabel(icon)
    icon_box.setFixedSize(22, 22)
    icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_box.setStyleSheet(f"background-color: {theme_module.rgba(color, 0.14)}; border-radius: 7px; font-size: 11px;")
    layout.addWidget(icon_box)

    label_widget = QLabel(label)
    label_widget.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 11px; background: transparent;")
    layout.addWidget(label_widget)

    value_label = QLabel("—")
    value_label.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; background: transparent;")
    layout.addWidget(value_label)

    return chip, value_label


class CanliSessionPage(QWidget):
    """Session screen shown during active driving and telemetry recording.

    Signals:
        session_ended: Emitted when the driver clicks 'End Session'.
        lap_selected:  Emitted when a completed lap is clicked (carries lap_number).
    """

    session_ended = pyqtSignal()
    lap_selected = pyqtSignal(int)

    def __init__(
        self, telemetry_receiver: TelemetryReceiver, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._receiver = telemetry_receiver
        self._last_lap_count = -1
        self._stale_warning_shown = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        # --- Top row: Status pill + Live Telemetry Chips ---
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._status_pill = QFrame()
        pill_layout = QHBoxLayout(self._status_pill)
        pill_layout.setContentsMargins(12, 6, 12, 6)
        pill_layout.setSpacing(6)
        self._status_dot = QLabel("●")
        pill_layout.addWidget(self._status_dot)
        self._status_text = QLabel("Waiting for session")
        self._status_text.setStyleSheet("font-size: 12px; font-weight: 600; background: transparent;")
        pill_layout.addWidget(self._status_text)
        top_row.addWidget(self._status_pill)

        top_row.addStretch(1)

        self._speed_chip, self._speed_value = _make_stat_chip("🏎️", "Speed", theme_module.BLUE)
        self._gear_chip, self._gear_value = _make_stat_chip("⚙️", "Gear", theme_module.PURPLE)
        self._throttle_chip, self._throttle_value = _make_stat_chip("⚡", "Throttle", theme_module.GREEN)
        self._rpm_chip, self._rpm_value = _make_stat_chip("📈", "RPM", theme_module.ORANGE)

        for chip in (self._speed_chip, self._gear_chip, self._throttle_chip, self._rpm_chip):
            top_row.addWidget(chip)
            chip.hide()

        layout.addLayout(top_row)

        # --- Session Header Info ---
        self._session_info_label = QLabel("Waiting for F1 25 session...")
        self._session_info_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(self._session_info_label)

        # --- Laps Header ---
        laps_header = QHBoxLayout()
        self._laps_title = QLabel("Completed Laps")
        self._laps_title.setStyleSheet("font-size: 14px; font-weight: 600;")
        laps_header.addWidget(self._laps_title)

        self._laps_hint = QLabel("(click any lap to open telemetry analysis)")
        self._laps_hint.setStyleSheet(f"font-size: 12px; color: {theme_module.TEXT_SECONDARY};")
        laps_header.addWidget(self._laps_hint)
        laps_header.addStretch(1)
        layout.addLayout(laps_header)

        # --- Laps List (interactive) ---
        self._lap_list = QListWidget()
        self._lap_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lap_list.setStyleSheet(
            f"QListWidget {{ background-color: {theme_module.SURFACE}; border: 1px solid {theme_module.BORDER};"
            f"  border-radius: 10px; padding: 6px; }}"
            f"QListWidget::item {{ height: 38px; padding-left: 12px; border-radius: 6px; margin-bottom: 2px; font-size: 13px; }}"
            f"QListWidget::item:hover {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.15)}; }}"
            f"QListWidget::item:selected {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.25)}; color: #FFFFFF; }}"
        )
        self._lap_list.itemClicked.connect(self._on_item_clicked)
        self._lap_list.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self._lap_list)

        # --- End Session Button ---
        self._end_button = QPushButton("End Session")
        self._end_button.setEnabled(False)
        self._end_button.setFixedHeight(40)
        self._end_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._end_button.setStyleSheet(
            f"QPushButton {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.1)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.ACCENT_RED, 0.25)}; border-radius: 10px;"
            f"  color: {theme_module.ACCENT_RED}; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.16)}; }}"
            f"QPushButton:disabled {{ color: {theme_module.TEXT_MUTED}; background-color: transparent;"
            f"  border-color: {theme_module.BORDER}; }}"
        )
        self._end_button.clicked.connect(self._on_end_session)
        layout.addWidget(self._end_button)

        self._timer = QTimer(self)
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)
        self._timer.timeout.connect(self._tick)

    def _on_theme_changed(self) -> None:
        """Re-applies correct pill and button styles on theme changes."""
        if not self._end_button.isEnabled():
            self._set_status_waiting()
        elif self._stale_warning_shown:
            self._set_status_disconnected()
        else:
            self._set_status_recording()

    def start_monitoring(self) -> None:
        """Called by MainWindow after starting telemetry."""
        self._last_lap_count = -1
        self._stale_warning_shown = False
        self._lap_list.clear()
        self._session_info_label.setText("Waiting for session...")
        self._set_status_recording()
        self._end_button.setEnabled(True)
        self._timer.start(_TICK_INTERVAL_MS)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        lap_number = item.data(Qt.ItemDataRole.UserRole)
        if lap_number is not None:
            logger.info("User selected lap %d from Live Session list", lap_number)
            self.lap_selected.emit(lap_number)

    def _tick(self) -> None:
        session = self._receiver.session_manager.current_session
        if session is not None and session.lap_count != self._last_lap_count:
            self._session_info_label.setText(
                f"{session.track.display_name} — {session.session_type.display_name} "
                f"— {session.lap_count} laps completed"
            )
            self._refresh_lap_list(session)
            self._last_lap_count = session.lap_count
            self._stale_warning_shown = False

        # Live telemetry display
        telemetry = self._receiver.session_manager.latest_telemetry
        if telemetry is not None:
            self._speed_value.setText(f"{int(telemetry.speed)} km/h")
            gear_text = "N" if telemetry.gear == 0 else "R" if telemetry.gear == -1 else f"{telemetry.gear}"
            self._gear_value.setText(gear_text)
            self._throttle_value.setText(f"{int(telemetry.throttle * 100)}%")
            self._rpm_value.setText(f"{int(telemetry.rpm)}")
            for chip in (self._speed_chip, self._gear_chip, self._throttle_chip, self._rpm_chip):
                chip.show()

        idle_seconds = self._receiver.seconds_since_last_packet()
        if idle_seconds is not None and idle_seconds > _STALE_THRESHOLD_SECONDS:
            if not self._stale_warning_shown:
                self._set_status_disconnected()
                self._stale_warning_shown = True
        elif self._stale_warning_shown:
            self._set_status_recording()
            self._stale_warning_shown = False

    def _refresh_lap_list(self, session) -> None:  # type: ignore[no-untyped-def]
        self._lap_list.clear()
        for lap in session.laps:
            minutes, seconds = divmod(lap.lap_time, 60)
            time_text = f"{int(minutes)}:{seconds:06.3f}"
            validity = "Valid" if lap.is_valid else "Invalid"
            item = QListWidgetItem(f"🏎️  Lap {lap.lap_number}    •    {time_text}    •    ({validity})    ➜  View Telemetry Analysis")
            item.setData(Qt.ItemDataRole.UserRole, lap.lap_number)
            if not lap.is_valid:
                item.setForeground(Qt.GlobalColor.gray)
            else:
                item.setForeground(Qt.GlobalColor.white)
            self._lap_list.addItem(item)

    def _set_status_waiting(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.TEXT_SECONDARY, 0.08)};"
            f"  border: 1px solid {theme_module.BORDER}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        self._status_text.setText("Waiting for session")
        self._status_text.setStyleSheet(f"color: {theme_module.TEXT_SECONDARY}; font-size: 12px; font-weight: 600; background: transparent;")

    def _set_status_recording(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.GREEN, 0.10)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.GREEN, 0.25)}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 10px; background: transparent;")
        self._status_text.setText("Telemetry recording")
        self._status_text.setStyleSheet(f"color: {theme_module.GREEN}; font-size: 12px; font-weight: 600; background: transparent;")

    def _set_status_disconnected(self) -> None:
        self._status_pill.setStyleSheet(
            f"QFrame {{ background-color: {theme_module.rgba(theme_module.ACCENT_RED, 0.10)};"
            f"  border: 1px solid {theme_module.rgba(theme_module.ACCENT_RED, 0.25)}; border-radius: 100px; }}"
        )
        self._status_dot.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 10px; background: transparent;")
        self._status_text.setText("No telemetry received")
        self._status_text.setStyleSheet(f"color: {theme_module.ACCENT_RED}; font-size: 12px; font-weight: 600; background: transparent;")
        logger.warning("Live Session: telemetry stream paused/idle.")

    def _on_end_session(self) -> None:
        self._timer.stop()
        self._receiver.stop()
        self._session_info_label.setText(
            self._session_info_label.text() + "  [Session completed]"
        )
        self._set_status_waiting()
        self._end_button.setEnabled(False)
        for chip in (self._speed_chip, self._gear_chip, self._throttle_chip, self._rpm_chip):
            chip.hide()
        logger.info("Session ended by user.")
        self.session_ended.emit()
