"""Master Live Dashboard Page (F1 Pit Wall Telemetry Console).

Implements the Mercedes Petronas F1 telemetry console layout:
- Left Column: Race Status, Circuit Map & Weather
- Center Column: Vehicle Chassis Thermal Heatmap, RPM Tachometer & Powertrain HUD
- Right Column: Driver Biometrics (Heart Rate ECG, Breaths, Stress Index)
"""

import time
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.ports.profile_repository import ProfileRepository
from f1_coach.infrastructure.f125_udp.telemetry_receiver import TelemetryReceiver
from f1_coach.presentation.f125.dashboard.car_thermal_widget import CarThermalWidget
from f1_coach.presentation.f125.dashboard.header_widget import DashboardHeaderWidget
from f1_coach.presentation.f125.dashboard.powertrain_hud_widget import PowertrainHUDWidget
from f1_coach.presentation.f125.dashboard.race_status_widget import RaceStatusWidget
from f1_coach.presentation.f125.dashboard.telemetry_curves_widget import TelemetryCurvesWidget
from f1_coach.presentation.f125.dashboard.weather_widget import WeatherWidget

_REFRESH_INTERVAL_MS = 40  # 25 FPS for smooth oscilloscope rendering


class LiveDashboardPage(QWidget):
    """Full-screen live telemetry and biometric dashboard."""

    def __init__(
        self,
        telemetry_receiver: TelemetryReceiver,
        profile_repo: ProfileRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._receiver = telemetry_receiver
        self._profile_repo = profile_repo
        self.setStyleSheet("background-color: #060B0D;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. Top Header Bar
        self._header = DashboardHeaderWidget()
        main_layout.addWidget(self._header)

        # 2. Main 3-Column Grid wrapped in ScrollArea for smaller monitors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cols_layout = QHBoxLayout(container)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(12)

        # --- LEFT COLUMN: Race Status + Weather ---
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        self._race_status = RaceStatusWidget()
        left_col.addWidget(self._race_status)

        self._weather = WeatherWidget()
        left_col.addWidget(self._weather)
        left_col.addStretch(1)

        cols_layout.addLayout(left_col, stretch=3)

        # --- CENTER COLUMN: Thermal Chassis + Powertrain HUD ---
        center_col = QVBoxLayout()
        center_col.setSpacing(10)

        self._car_thermal = CarThermalWidget()
        center_col.addWidget(self._car_thermal)

        self._powertrain = PowertrainHUDWidget()
        center_col.addWidget(self._powertrain)

        cols_layout.addLayout(center_col, stretch=4)

        # --- RIGHT COLUMN: Control Telemetry (Throttle, Brake & Speed: Live vs Ideal) ---
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        self._telemetry_curves = TelemetryCurvesWidget()
        right_col.addWidget(self._telemetry_curves)
        right_col.addStretch(1)

        cols_layout.addLayout(right_col, stretch=3)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Refresh timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._update_profile_info()

    def showEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().showEvent(event)
        self._update_profile_info()
        if not self._timer.isActive():
            self._timer.start(_REFRESH_INTERVAL_MS)

    def hideEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().hideEvent(event)
        pass

    def _update_profile_info(self) -> None:
        if self._profile_repo is not None:
            profile = self._profile_repo.get_current()
            if profile and profile.name:
                self._header.set_driver_info(profile.name, "44")

    def _on_tick(self) -> None:
        snapshot = self._receiver.live_snapshot

        # Feed reference best lap to curve comparator
        session = self._receiver.session_manager.current_session
        if session is not None and session.best_lap is not None:
            self._telemetry_curves.set_reference_lap(session.best_lap)

        self._race_status.update_snapshot(snapshot)
        self._weather.update_snapshot(snapshot)
        self._car_thermal.update_snapshot(snapshot)
        self._powertrain.update_snapshot(snapshot)
        self._telemetry_curves.tick(snapshot)
