"""Top header bar for the F1 Pit Wall Dashboard.

Displays team branding, driver identity, car number badge, and session indicator.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class DashboardHeaderWidget(QWidget):
    """Header component featuring team identity and driver badge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        # --- Left: Team Logo & Name ---
        team_layout = QHBoxLayout()
        team_layout.setSpacing(12)

        logo_box = QFrame()
        logo_box.setFixedSize(44, 44)
        logo_box.setStyleSheet(
            "QFrame { background-color: #0E2226; border: 1.5px solid #00D2BE; border-radius: 22px; }"
        )
        logo_inner = QHBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel("⭐")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet("font-size: 18px; color: #FFFFFF; background: transparent;")
        logo_inner.addWidget(logo_icon)
        team_layout.addWidget(logo_box)

        team_text_layout = QVBoxLayout()
        team_text_layout.setSpacing(1)
        team_title = QLabel("PETRONAS")
        team_title.setStyleSheet("font-size: 15px; font-weight: 900; letter-spacing: 2px; color: #00D2BE;")
        team_sub = QLabel("MERCEDES-AMG FORMULA ONE TEAM")
        team_sub.setStyleSheet("font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: #7A969B;")
        team_text_layout.addWidget(team_title)
        team_text_layout.addWidget(team_sub)
        team_layout.addLayout(team_text_layout)

        layout.addLayout(team_layout)
        layout.addStretch(1)

        # --- Right: Driver Name, Number & Status Badge ---
        driver_layout = QHBoxLayout()
        driver_layout.setSpacing(12)

        self._driver_name_label = QLabel("L. HAMILTON")
        self._driver_name_label.setStyleSheet(
            "font-size: 20px; font-weight: 900; letter-spacing: 2px; color: #E6F4F1;"
        )
        driver_layout.addWidget(self._driver_name_label)

        self._driver_number_badge = QLabel("44")
        self._driver_number_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._driver_number_badge.setFixedSize(36, 32)
        self._driver_number_badge.setStyleSheet(
            "QLabel { background-color: #00D2BE; color: #081012; font-size: 16px; font-weight: 900; "
            "border-radius: 6px; }"
        )
        driver_layout.addWidget(self._driver_number_badge)

        layout.addLayout(driver_layout)

    def set_driver_info(self, name: str, number: str = "44") -> None:
        """Update driver profile name and number."""
        if name:
            self._driver_name_label.setText(name.upper())
        if number:
            self._driver_number_badge.setText(str(number))
