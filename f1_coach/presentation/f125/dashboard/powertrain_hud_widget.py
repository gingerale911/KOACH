"""Powertrain, RPM Tachometer & System Gauges Widget.

Renders an animated horizontal LED tachometer, gear/speed HUD,
engine temperature bar, and fuel/ERS battery level meters.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot


class RPMBarWidget(QWidget):
    """Horizontal tachometer LED gauge with redline hash marks."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)
        self._rpm: int = 11450
        self._max_rpm: int = 13500

    def set_rpm(self, rpm: int, max_rpm: int = 13500) -> None:
        self._rpm = max(0, rpm)
        self._max_rpm = max(1000, max_rpm)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = 16
        bar_y = 6

        # Outer track background
        painter.setPen(QPen(QColor(20, 40, 44), 1.5))
        painter.setBrush(QColor(8, 14, 16))
        painter.drawRoundedRect(QRectF(1, bar_y, w - 2, bar_h), 4, 4)

        # Active fill ratio
        ratio = max(0.0, min(1.0, self._rpm / float(self._max_rpm)))
        fill_w = ratio * (w - 4)

        if fill_w > 0:
            # Gradient: Teal -> Yellow -> Orange -> Crimson Redline
            grad = QLinearGradient(2, 0, w - 2, 0)
            grad.setColorAt(0.0, QColor(0, 210, 190))
            grad.setColorAt(0.65, QColor(0, 210, 190))
            grad.setColorAt(0.78, QColor(234, 179, 8))
            grad.setColorAt(0.88, QColor(249, 115, 22))
            grad.setColorAt(1.0, QColor(239, 68, 68))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(2, bar_y + 1, fill_w, bar_h - 2), 3, 3)

        # Redline hash stripes at the far right
        hash_start = 0.88 * w
        painter.setPen(QPen(QColor(239, 68, 68, 180), 1.5))
        for x in range(int(hash_start), int(w - 6), 5):
            painter.drawLine(x, bar_y + 2, x + 3, bar_y + bar_h - 2)

        # Scale tick marks (0, 2000, 4000, 6000, 8000, 10000, 12000)
        painter.setPen(QColor(122, 150, 155))
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        painter.setFont(font)

        ticks = [0, 2000, 4000, 6000, 8000, 10000, 12000]
        for t in ticks:
            tx = 2 + (t / float(self._max_rpm)) * (w - 4)
            painter.drawLine(int(tx), bar_y + bar_h, int(tx), bar_y + bar_h + 3)
            painter.drawText(QRectF(tx - 15, bar_y + bar_h + 3, 30, 12), Qt.AlignmentFlag.AlignCenter, f"{t:,}")


class PowertrainHUDWidget(QFrame):
    """Bottom center console with RPM bar, engine temp, and fuel meters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #0B1618; border: 1px solid #14282B; border-radius: 12px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(8)

        # --- Top Header: RPM Title & Digital Speed/Gear ---
        top_row = QHBoxLayout()
        rpm_title = QLabel("RPM")
        rpm_title.setStyleSheet("font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #00D2BE; background: transparent;")
        top_row.addWidget(rpm_title)

        self._rpm_digital_label = QLabel("11,450 RPM")
        self._rpm_digital_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #E6F4F1; background: transparent;")
        top_row.addWidget(self._rpm_digital_label)

        top_row.addStretch(1)

        self._gear_label = QLabel("GEAR 7")
        self._gear_label.setStyleSheet(
            "background-color: #0E292A; border: 1px solid #00D2BE; border-radius: 6px; "
            "color: #00D2BE; font-size: 12px; font-weight: 800; padding: 2px 8px;"
        )
        top_row.addWidget(self._gear_label)

        self._speed_label = QLabel("287 KM/H")
        self._speed_label.setStyleSheet("font-size: 14px; font-weight: 900; color: #E6F4F1; background: transparent;")
        top_row.addWidget(self._speed_label)

        layout.addLayout(top_row)

        # --- Animated Tachometer Bar ---
        self._rpm_bar = RPMBarWidget()
        layout.addWidget(self._rpm_bar)

        # --- Bottom Meters: Engine Temp & Fuel % ---
        meters_row = QHBoxLayout()
        meters_row.setSpacing(16)

        # Engine Temp
        temp_box = QVBoxLayout()
        temp_box.setSpacing(2)
        t_header = QHBoxLayout()
        t_title = QLabel("ENGINE TEMP (C)")
        t_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #7A969B; background: transparent;")
        self._engine_temp_val = QLabel("95° C")
        self._engine_temp_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #00D2BE; background: transparent;")
        t_header.addWidget(t_title)
        t_header.addStretch(1)
        t_header.addWidget(self._engine_temp_val)
        temp_box.addLayout(t_header)

        self._temp_bar = QProgressBar()
        self._temp_bar.setRange(0, 140)
        self._temp_bar.setValue(95)
        self._temp_bar.setTextVisible(False)
        self._temp_bar.setFixedHeight(8)
        self._temp_bar.setStyleSheet(
            "QProgressBar { background-color: #081012; border: 1px solid #14282B; border-radius: 4px; }"
            "QProgressBar::chunk { background-color: #00D2BE; border-radius: 3px; }"
        )
        temp_box.addWidget(self._temp_bar)
        meters_row.addLayout(temp_box)

        # Fuel %
        fuel_box = QVBoxLayout()
        fuel_box.setSpacing(2)
        f_header = QHBoxLayout()
        f_title = QLabel("FUEL (%)")
        f_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #7A969B; background: transparent;")
        self._fuel_val = QLabel("52.4%")
        self._fuel_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #00D2BE; background: transparent;")
        f_header.addWidget(f_title)
        f_header.addStretch(1)
        f_header.addWidget(self._fuel_val)
        fuel_box.addLayout(f_header)

        self._fuel_bar = QProgressBar()
        self._fuel_bar.setRange(0, 100)
        self._fuel_bar.setValue(52)
        self._fuel_bar.setTextVisible(False)
        self._fuel_bar.setFixedHeight(8)
        self._fuel_bar.setStyleSheet(
            "QProgressBar { background-color: #081012; border: 1px solid #14282B; border-radius: 4px; }"
            "QProgressBar::chunk { background-color: #00D2BE; border-radius: 3px; }"
        )
        fuel_box.addWidget(self._fuel_bar)
        meters_row.addLayout(fuel_box)

        layout.addLayout(meters_row)

    def update_snapshot(self, snapshot: LiveTelemetrySnapshot) -> None:
        self._rpm_bar.set_rpm(snapshot.engine_rpm, snapshot.max_rpm)
        self._rpm_digital_label.setText(f"{snapshot.engine_rpm:,} RPM")

        gear_text = "N" if snapshot.gear == 0 else "R" if snapshot.gear == -1 else f"{snapshot.gear}"
        self._gear_label.setText(f"GEAR {gear_text}")
        self._speed_label.setText(f"{snapshot.speed_kmh} KM/H")

        self._engine_temp_val.setText(f"{snapshot.engine_temperature}° C")
        self._temp_bar.setValue(snapshot.engine_temperature)

        fuel_pct = snapshot.fuel_percent
        self._fuel_val.setText(f"{fuel_pct:.1f}%")
        self._fuel_bar.setValue(int(fuel_pct))
