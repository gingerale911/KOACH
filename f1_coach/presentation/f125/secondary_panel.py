"""SecondaryPanel — Layer 2: Horizontal tab bar for F1 25.

Displays navigation tabs for Live Session, Live Dashboard (Pit Wall),
Lap Analysis, and Session History.
Keeps tabs accessible at all times during active sessions so the user
can seamlessly switch between live monitoring, visual telemetry dashboard,
detailed telemetry charts, and past session logs while driving.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from f1_coach.presentation.f125 import palette

_PANEL_HEIGHT = 48


class SecondaryPanel(QWidget):
    """F1 25 horizontal tab navigation bar.

    Signals:
        live_session_clicked:    "Live Session" tab clicked.
        live_dashboard_clicked:  "Live Dashboard" tab clicked.
        lap_analysis_clicked:    "Lap Analysis" tab clicked.
        session_history_clicked: "Session History" tab clicked.
    """

    live_session_clicked = pyqtSignal()
    live_dashboard_clicked = pyqtSignal()
    lap_analysis_clicked = pyqtSignal()
    session_history_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_PANEL_HEIGHT)
        self.setObjectName("SecondaryPanel")
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        self._live_session_button = QPushButton("🔴 Live Session")
        self._live_session_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._live_session_button.clicked.connect(self.live_session_clicked.emit)
        layout.addWidget(self._live_session_button)

        self._live_dashboard_button = QPushButton("🏁 Live Dashboard")
        self._live_dashboard_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._live_dashboard_button.clicked.connect(self.live_dashboard_clicked.emit)
        layout.addWidget(self._live_dashboard_button)

        self._lap_analysis_button = QPushButton("📊 Lap Analysis")
        self._lap_analysis_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lap_analysis_button.clicked.connect(self.lap_analysis_clicked.emit)
        layout.addWidget(self._lap_analysis_button)

        self._session_history_button = QPushButton("📁 Session History")
        self._session_history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._session_history_button.clicked.connect(self.session_history_clicked.emit)
        layout.addWidget(self._session_history_button)

        layout.addStretch(1)
        self._current_tab = "live"
        self.set_active_tab("live")

    def set_active_tab(self, tab: str) -> None:
        """Sets active tab highlighting: 'live', 'dashboard', 'analysis', or 'history'."""
        self._current_tab = tab
        buttons = [
            ("live", self._live_session_button),
            ("dashboard", self._live_dashboard_button),
            ("analysis", self._lap_analysis_button),
            ("history", self._session_history_button),
        ]
        for name, btn in buttons:
            if name == tab:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {palette.ACCENT}; color: {palette.ON_ACCENT}; font-weight: 700;"
                    f"  border: 1px solid {palette.ACCENT}; border-radius: 8px; padding: 6px 16px; font-size: 12px; }}"
                    f"QPushButton:hover {{ background-color: {palette.ACCENT_HOVER}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {palette.SURFACE}; color: {palette.TEXT_SECONDARY}; font-weight: 600;"
                    f"  border: 1px solid {palette.BORDER}; border-radius: 8px; padding: 6px 16px; font-size: 12px; }}"
                    f"QPushButton:hover {{ background-color: {palette.rgba(palette.TEXT_PRIMARY, 0.08)}; color: {palette.TEXT_PRIMARY}; border-color: {palette.ACCENT}; }}"
                )

    def open_panel(self) -> None:
        """Called when opening F1 25 session."""
        self.show()

    def close_panel(self) -> None:
        """Called when navigating outside F1 25."""
        self.hide()

    def set_navigation_locked(self, locked: bool) -> None:
        """Keep navigation accessible so user can freely switch tabs during races."""
        self._live_session_button.setEnabled(True)
        self._live_dashboard_button.setEnabled(True)
        self._lap_analysis_button.setEnabled(True)
        self._session_history_button.setEnabled(True)
