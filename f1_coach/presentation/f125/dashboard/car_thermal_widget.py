"""Car Thermal & Dynamics Widget.

Renders a top-down F1 chassis with real-time color-coded thermal wear
and precise pressure and temperature callouts for all four wheels and brakes.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot


def _temp_color(temp: int) -> QColor:
    """Return color gradient based on tire temperature in Celsius."""
    if temp < 85:
        return QColor(56, 189, 248)    # Cold: Cyan / Blue
    elif temp <= 105:
        return QColor(0, 210, 190)    # Optimal: Petronas Teal
    elif temp <= 115:
        return QColor(249, 115, 22)    # Warm: Orange
    else:
        return QColor(239, 68, 68)     # Hot: Red


def _brake_color(temp: int) -> QColor:
    """Return color for brake rotor temperature."""
    if temp < 400:
        return QColor(0, 210, 190)
    elif temp < 700:
        return QColor(249, 115, 22)
    else:
        return QColor(239, 68, 68)


class CarChassisCanvas(QWidget):
    """Custom top-down rendering of an F1 chassis with heat-reactive tires."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 360)
        self._fl_temp = 104
        self._fr_temp = 105
        self._rl_temp = 113
        self._rr_temp = 115

    def set_temperatures(self, fl: int, fr: int, rl: int, rr: int) -> None:
        self._fl_temp = fl
        self._fr_temp = fr
        self._rl_temp = rl
        self._rr_temp = rr
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Chassis scaling dimensions
        scale = min(self.width() / 240.0, self.height() / 380.0)

        painter.save()
        painter.translate(cx, cy)
        painter.scale(scale, scale)

        # --- Draw Top-Down F1 Car Body ---
        # Main Carbon Monocoque / Nose
        body_path = QPainterPath()
        body_path.moveTo(0, -160)            # Nose tip
        body_path.lineTo(15, -130)           # Front cone
        body_path.lineTo(20, -70)            # Front bulkhead
        body_path.lineTo(36, -30)            # Sidepod intake
        body_path.lineTo(38, 40)             # Sidepod body
        body_path.lineTo(24, 100)            # Engine cover taper
        body_path.lineTo(16, 140)            # Rear crash structure
        body_path.lineTo(0, 150)             # Rear exhaust
        body_path.lineTo(-16, 140)
        body_path.lineTo(-24, 100)
        body_path.lineTo(-38, 40)
        body_path.lineTo(-36, -30)
        body_path.lineTo(-20, -70)
        body_path.lineTo(-15, -130)
        body_path.closeSubpath()

        # Carbon gradient fill
        carbon_grad = QLinearGradient(0, -160, 0, 150)
        carbon_grad.setColorAt(0.0, QColor(40, 50, 54))
        carbon_grad.setColorAt(0.5, QColor(25, 32, 35))
        carbon_grad.setColorAt(1.0, QColor(15, 20, 22))

        painter.setPen(QPen(QColor(0, 210, 190, 120), 1.5))
        painter.setBrush(QBrush(carbon_grad))
        painter.drawPath(body_path)

        # Cockpit & Halo
        cockpit_rect = QRectF(-11, -45, 22, 45)
        painter.setPen(QPen(QColor(0, 210, 190), 1))
        painter.setBrush(QColor(8, 12, 14))
        painter.drawRoundedRect(cockpit_rect, 10, 10)

        # Driver Helmet (Teal / Yellow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 210, 190))
        painter.drawEllipse(QPointF(0, -25), 6, 7)

        # Front Wing
        fw_path = QPainterPath()
        fw_path.moveTo(-60, -152)
        fw_path.lineTo(60, -152)
        fw_path.lineTo(60, -138)
        fw_path.lineTo(-60, -138)
        fw_path.closeSubpath()
        painter.setPen(QPen(QColor(0, 210, 190, 80), 1))
        painter.setBrush(QColor(30, 38, 42))
        painter.drawPath(fw_path)

        # Rear Wing
        rw_path = QPainterPath()
        rw_path.moveTo(-54, 135)
        rw_path.lineTo(54, 135)
        rw_path.lineTo(54, 152)
        rw_path.lineTo(-54, 152)
        rw_path.closeSubpath()
        painter.drawPath(rw_path)

        # Suspension Wishbones
        susp_pen = QPen(QColor(120, 140, 145), 1.5)
        painter.setPen(susp_pen)
        # Front Left
        painter.drawLine(QPointF(-20, -70), QPointF(-55, -80))
        painter.drawLine(QPointF(-18, -60), QPointF(-55, -65))
        # Front Right
        painter.drawLine(QPointF(20, -70), QPointF(55, -80))
        painter.drawLine(QPointF(18, -60), QPointF(55, -65))
        # Rear Left
        painter.drawLine(QPointF(-22, 80), QPointF(-55, 75))
        painter.drawLine(QPointF(-20, 100), QPointF(-55, 95))
        # Rear Right
        painter.drawLine(QPointF(22, 80), QPointF(55, 75))
        painter.drawLine(QPointF(20, 100), QPointF(55, 95))

        # --- Draw 4 Wheels (Color-coded based on temperature) ---
        tire_w = 20
        tire_h = 44

        def draw_tire(tx: float, ty: float, temp: int) -> None:
            col = _temp_color(temp)
            # Outer glow
            glow = QColor(col.red(), col.green(), col.blue(), 50)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawRoundedRect(QRectF(tx - 3, ty - 3, tire_w + 6, tire_h + 6), 7, 7)

            # Tire body
            painter.setPen(QPen(col, 2))
            painter.setBrush(QColor(col.red(), col.green(), col.blue(), 180))
            painter.drawRoundedRect(QRectF(tx, ty, tire_w, tire_h), 5, 5)

            # Inner rim
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 20, 22))
            painter.drawRoundedRect(QRectF(tx + 4, ty + 6, tire_w - 8, tire_h - 12), 3, 3)

        # FL, FR, RL, RR
        draw_tire(-75, -95, self._fl_temp)
        draw_tire(55, -95, self._fr_temp)
        draw_tire(-75, 65, self._rl_temp)
        draw_tire(55, 65, self._rr_temp)

        painter.restore()


class WheelCalloutWidget(QWidget):
    """Corner telemetry info block: Temperature, Pressure, and Brakes."""

    def __init__(self, corner_name: str, align_right: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        align = Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft

        # Header: e.g. FL TIRE
        title = QLabel(f"{corner_name} TIRE")
        title.setAlignment(align)
        title.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #7A969B;")
        layout.addWidget(title)

        # Tire Temp & Pressure row
        tp_row = QHBoxLayout()
        tp_row.setSpacing(8)
        if align_right:
            tp_row.addStretch(1)

        self._temp_label = QLabel("104° C")
        self._temp_label.setStyleSheet("font-size: 14px; font-weight: 800; color: #F97316;")
        tp_row.addWidget(self._temp_label)

        self._pressure_label = QLabel("1.2 bar")
        self._pressure_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #00D2BE;")
        tp_row.addWidget(self._pressure_label)

        if not align_right:
            tp_row.addStretch(1)
        layout.addLayout(tp_row)

        # Brake Header & Temp
        brake_title = QLabel(f"{corner_name} BRAKES")
        brake_title.setAlignment(align)
        brake_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #7A969B; margin-top: 2px;")
        layout.addWidget(brake_title)

        self._brake_label = QLabel("650° C")
        self._brake_label.setAlignment(align)
        self._brake_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #EF4444;")
        layout.addWidget(self._brake_label)

    def update_values(self, tyre_temp: int, pressure_bar: float, brake_temp: int) -> None:
        col = _temp_color(tyre_temp).name()
        bcol = _brake_color(brake_temp).name()

        self._temp_label.setText(f"{tyre_temp}° C")
        self._temp_label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {col};")

        self._pressure_label.setText(f"{pressure_bar:.1f} bar")

        self._brake_label.setText(f"{brake_temp}° C")
        self._brake_label.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {bcol};")


class CarThermalWidget(QFrame):
    """Central panel integrating chassis canvas with 4-wheel telemetry callouts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #081012; border: 1px solid #14282B; border-radius: 12px; }"
        )

        grid = QGridLayout(self)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(6)

        # Wheel Callouts
        self._fl_callout = WheelCalloutWidget("FL", align_right=True)
        self._fr_callout = WheelCalloutWidget("FR", align_right=False)
        self._rl_callout = WheelCalloutWidget("RL", align_right=True)
        self._rr_callout = WheelCalloutWidget("RR", align_right=False)

        self._chassis_canvas = CarChassisCanvas()

        # Layout positioning:
        # Row 0: FL, Chassis (spanning rows 0 & 1), FR
        # Row 1: RL, Chassis, RR
        grid.addWidget(self._fl_callout, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._chassis_canvas, 0, 1, 2, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._fr_callout, 0, 2, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._rl_callout, 1, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._rr_callout, 1, 2, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

    def update_snapshot(self, snapshot: LiveTelemetrySnapshot) -> None:
        self._fl_callout.update_values(
            snapshot.fl_tyre_temp, snapshot.fl_tyre_pressure_bar, snapshot.fl_brake_temp
        )
        self._fr_callout.update_values(
            snapshot.fr_tyre_temp, snapshot.fr_tyre_pressure_bar, snapshot.fr_brake_temp
        )
        self._rl_callout.update_values(
            snapshot.rl_tyre_temp, snapshot.rl_tyre_pressure_bar, snapshot.rl_brake_temp
        )
        self._rr_callout.update_values(
            snapshot.rr_tyre_temp, snapshot.rr_tyre_pressure_bar, snapshot.rr_brake_temp
        )
        self._chassis_canvas.set_temperatures(
            snapshot.fl_tyre_temp, snapshot.fr_tyre_temp, snapshot.rl_tyre_temp, snapshot.rr_tyre_temp
        )
