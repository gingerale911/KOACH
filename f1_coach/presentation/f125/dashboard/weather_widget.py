"""Weather Conditions Widget.

Displays ambient air temperature, cloud cover, humidity, air pressure, and wind speed.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot


class WeatherWidget(QFrame):
    """Weather and atmospheric telemetry widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #0B1618; border: 1px solid #14282B; border-radius: 12px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        self._air_temp_label = self._create_stat_column(layout, "Air Temperature", "23.4° C")
        self._cloud_label = self._create_stat_column(layout, "Cloud Cover", "13%")
        self._humidity_label = self._create_stat_column(layout, "Humidity", "75%")
        self._pressure_label = self._create_stat_column(layout, "Pressure", "1013 mb")
        self._wind_label = self._create_stat_column(layout, "Wind Speed", "7.00 km/h")

    def _create_stat_column(self, layout: QHBoxLayout, label: str, default_val: str) -> QLabel:
        col = QVBoxLayout()
        col.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #7A969B; background: transparent;")
        col.addWidget(lbl)

        val = QLabel(default_val)
        val.setStyleSheet("font-size: 13px; font-weight: 800; color: #E6F4F1; background: transparent;")
        col.addWidget(val)

        layout.addLayout(col)
        return val

    def update_snapshot(self, snapshot: LiveTelemetrySnapshot) -> None:
        self._air_temp_label.setText(f"{snapshot.air_temperature:.1f}° C")
        self._cloud_label.setText(f"{snapshot.rain_percentage}%")
        self._humidity_label.setText(f"{snapshot.humidity}%")
        self._pressure_label.setText(f"{snapshot.air_pressure_mb} mb")
        self._wind_label.setText(f"{snapshot.wind_speed_kmh:.2f} km/h")
