"""Car Thermal & Dynamics Widget.

Renders a top-down F1 chassis with green-to-red health colours for tyre wear
and wing damage, plus temperature, pressure and wear callouts for each wheel.
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

_NEUTRAL_HEALTH = QColor(70, 84, 88)
_MUTED_TEXT = "#7A969B"
_DAMAGE_CHIPS: tuple[tuple[str, str], ...] = (
    ("FL WING", "front_left_wing_damage"),
    ("FR WING", "front_right_wing_damage"),
    ("REAR WING", "rear_wing_damage"),
    ("FLOOR", "floor_damage"),
    ("DIFFUSER", "diffuser_damage"),
    ("SIDEPOD", "sidepod_damage"),
)


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


def _health_color(damage_pct: float) -> QColor:
    """Map a 0-100 wear or damage percentage onto green (healthy), amber, red (worn)."""
    t = max(0.0, min(1.0, damage_pct / 100.0))
    green = (34, 197, 94)
    amber = (234, 179, 8)
    red = (239, 68, 68)
    if t < 0.5:
        start, end, local = green, amber, t * 2
    else:
        start, end, local = amber, red, (t - 0.5) * 2
    r, g, b = (round(s + (e - s) * local) for s, e in zip(start, end))
    return QColor(r, g, b)


class CarChassisCanvas(QWidget):
    """Top-down F1 chassis with tyre wear and wing damage as health colours."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(220, 360)
        self._has_data = False
        self._tyre_wear: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # RL, RR, FL, FR
        self._wing_damage: tuple[int, int, int] = (0, 0, 0)  # front left, front right, rear

    def set_health(
        self,
        has_data: bool,
        tyre_wear: tuple[float, float, float, float],
        wing_damage: tuple[int, int, int],
    ) -> None:
        self._has_data = has_data
        self._tyre_wear = tyre_wear
        self._wing_damage = wing_damage
        self.update()

    def _health(self, damage_pct: float) -> QColor:
        return _health_color(damage_pct) if self._has_data else _NEUTRAL_HEALTH

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        scale = min(self.width() / 240.0, self.height() / 380.0)

        painter.save()
        painter.translate(cx, cy)
        painter.scale(scale, scale)

        body_path = QPainterPath()
        body_path.moveTo(0, -160)
        body_path.lineTo(15, -130)
        body_path.lineTo(20, -70)
        body_path.lineTo(36, -30)
        body_path.lineTo(38, 40)
        body_path.lineTo(24, 100)
        body_path.lineTo(16, 140)
        body_path.lineTo(0, 150)
        body_path.lineTo(-16, 140)
        body_path.lineTo(-24, 100)
        body_path.lineTo(-38, 40)
        body_path.lineTo(-36, -30)
        body_path.lineTo(-20, -70)
        body_path.lineTo(-15, -130)
        body_path.closeSubpath()

        carbon_grad = QLinearGradient(0, -160, 0, 150)
        carbon_grad.setColorAt(0.0, QColor(40, 50, 54))
        carbon_grad.setColorAt(0.5, QColor(25, 32, 35))
        carbon_grad.setColorAt(1.0, QColor(15, 20, 22))

        painter.setPen(QPen(QColor(0, 210, 190, 120), 1.5))
        painter.setBrush(QBrush(carbon_grad))
        painter.drawPath(body_path)

        painter.setPen(QPen(QColor(0, 210, 190), 1))
        painter.setBrush(QColor(8, 12, 14))
        painter.drawRoundedRect(QRectF(-11, -45, 22, 45), 10, 10)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 210, 190))
        painter.drawEllipse(QPointF(0, -25), 6, 7)

        front_left_wing, front_right_wing, rear_wing = (self._health(v) for v in self._wing_damage)
        for x0, wing_color in ((-60.0, front_left_wing), (0.0, front_right_wing)):
            painter.setPen(QPen(wing_color, 1.5))
            painter.setBrush(QColor(wing_color.red(), wing_color.green(), wing_color.blue(), 170))
            painter.drawRect(QRectF(x0, -152, 60, 14))

        painter.setPen(QPen(rear_wing, 1.5))
        painter.setBrush(QColor(rear_wing.red(), rear_wing.green(), rear_wing.blue(), 170))
        painter.drawRect(QRectF(-54, 135, 108, 17))

        susp_pen = QPen(QColor(120, 140, 145), 1.5)
        painter.setPen(susp_pen)
        painter.drawLine(QPointF(-20, -70), QPointF(-55, -80))
        painter.drawLine(QPointF(-18, -60), QPointF(-55, -65))
        painter.drawLine(QPointF(20, -70), QPointF(55, -80))
        painter.drawLine(QPointF(18, -60), QPointF(55, -65))
        painter.drawLine(QPointF(-22, 80), QPointF(-55, 75))
        painter.drawLine(QPointF(-20, 100), QPointF(-55, 95))
        painter.drawLine(QPointF(22, 80), QPointF(55, 75))
        painter.drawLine(QPointF(20, 100), QPointF(55, 95))

        tire_w = 20
        tire_h = 44

        def draw_tire(tx: float, ty: float, col: QColor) -> None:
            glow = QColor(col.red(), col.green(), col.blue(), 50)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawRoundedRect(QRectF(tx - 3, ty - 3, tire_w + 6, tire_h + 6), 7, 7)

            painter.setPen(QPen(col, 2))
            painter.setBrush(QColor(col.red(), col.green(), col.blue(), 180))
            painter.drawRoundedRect(QRectF(tx, ty, tire_w, tire_h), 5, 5)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 20, 22))
            painter.drawRoundedRect(QRectF(tx + 4, ty + 6, tire_w - 8, tire_h - 12), 3, 3)

        # Tyre wear is ordered RL, RR, FL, FR in the telemetry packet
        draw_tire(-75, -95, self._health(self._tyre_wear[2]))
        draw_tire(55, -95, self._health(self._tyre_wear[3]))
        draw_tire(-75, 65, self._health(self._tyre_wear[0]))
        draw_tire(55, 65, self._health(self._tyre_wear[1]))

        painter.restore()


class WheelCalloutWidget(QWidget):
    """Corner telemetry info block: Temperature, Pressure, Wear and Brakes."""

    def __init__(self, corner_name: str, align_right: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        align = Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft

        title = QLabel(f"{corner_name} TIRE")
        title.setAlignment(align)
        title.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1px; color: #7A969B;")
        layout.addWidget(title)

        tp_row = QHBoxLayout()
        tp_row.setSpacing(8)
        if align_right:
            tp_row.addStretch(1)

        self._temp_label = QLabel("--° C")
        self._temp_label.setStyleSheet("font-size: 14px; font-weight: 800; color: #F97316;")
        tp_row.addWidget(self._temp_label)

        self._pressure_label = QLabel("-- bar")
        self._pressure_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #00D2BE;")
        tp_row.addWidget(self._pressure_label)

        if not align_right:
            tp_row.addStretch(1)
        layout.addLayout(tp_row)

        self._wear_label = QLabel("WEAR --")
        self._wear_label.setAlignment(align)
        self._wear_label.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {_MUTED_TEXT};")
        layout.addWidget(self._wear_label)

        brake_title = QLabel(f"{corner_name} BRAKES")
        brake_title.setAlignment(align)
        brake_title.setStyleSheet(f"font-size: 9px; font-weight: 700; color: {_MUTED_TEXT}; margin-top: 2px;")
        layout.addWidget(brake_title)

        self._brake_label = QLabel("-- ° C")
        self._brake_label.setAlignment(align)
        self._brake_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #7A969B;")
        layout.addWidget(self._brake_label)

    def update_values(
        self,
        tyre_temp: int,
        pressure_bar: float,
        brake_temp: int,
        wear_pct: float | None,
    ) -> None:
        col = _temp_color(tyre_temp).name()
        bcol = _brake_color(brake_temp).name()

        self._temp_label.setText(f"{tyre_temp}° C")
        self._temp_label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {col};")

        self._pressure_label.setText(f"{pressure_bar:.1f} bar")

        if wear_pct is None:
            self._wear_label.setText("WEAR --")
            self._wear_label.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {_MUTED_TEXT};")
        else:
            wcol = _health_color(wear_pct).name()
            self._wear_label.setText(f"WEAR {wear_pct:.0f}%")
            self._wear_label.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {wcol};")

        self._brake_label.setText(f"{brake_temp}° C")
        self._brake_label.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {bcol};")


def _style_chip(chip: QLabel, name: str, damage: int, has_data: bool) -> None:
    if has_data:
        border = _health_color(damage).name()
        chip.setText(f"{name} {damage}%")
    else:
        border = _MUTED_TEXT
        chip.setText(f"{name} --")
    chip.setStyleSheet(
        "font-size: 10px; font-weight: 800; color: #E6F4F1; background: transparent; "
        f"border: 1px solid {border}; border-radius: 6px; padding: 3px 6px;"
    )


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

        self._fl_callout = WheelCalloutWidget("FL", align_right=True)
        self._fr_callout = WheelCalloutWidget("FR", align_right=False)
        self._rl_callout = WheelCalloutWidget("RL", align_right=True)
        self._rr_callout = WheelCalloutWidget("RR", align_right=False)

        self._chassis_canvas = CarChassisCanvas()

        grid.addWidget(self._fl_callout, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._chassis_canvas, 0, 1, 2, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._fr_callout, 0, 2, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self._rl_callout, 1, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self._rr_callout, 1, 2, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

        chip_grid = QGridLayout()
        chip_grid.setSpacing(6)
        self._damage_chips: list[QLabel] = []
        for index in range(len(_DAMAGE_CHIPS)):
            chip = QLabel()
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._damage_chips.append(chip)
            chip_grid.addWidget(chip, index // 3, index % 3)
        grid.addLayout(chip_grid, 2, 0, 1, 3)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

    def update_snapshot(self, snapshot: LiveTelemetrySnapshot) -> None:
        has_data = snapshot.damage_received
        wear = snapshot.tyres_wear_pct

        def wear_for(index: int) -> float | None:
            return wear[index] if has_data else None

        self._fl_callout.update_values(
            snapshot.fl_tyre_temp, snapshot.fl_tyre_pressure_bar, snapshot.fl_brake_temp, wear_for(2)
        )
        self._fr_callout.update_values(
            snapshot.fr_tyre_temp, snapshot.fr_tyre_pressure_bar, snapshot.fr_brake_temp, wear_for(3)
        )
        self._rl_callout.update_values(
            snapshot.rl_tyre_temp, snapshot.rl_tyre_pressure_bar, snapshot.rl_brake_temp, wear_for(0)
        )
        self._rr_callout.update_values(
            snapshot.rr_tyre_temp, snapshot.rr_tyre_pressure_bar, snapshot.rr_brake_temp, wear_for(1)
        )
        self._chassis_canvas.set_health(
            has_data,
            wear,
            (
                snapshot.front_left_wing_damage,
                snapshot.front_right_wing_damage,
                snapshot.rear_wing_damage,
            ),
        )
        for chip, (name, attr) in zip(self._damage_chips, _DAMAGE_CHIPS):
            _style_chip(chip, name, getattr(snapshot, attr), has_data)
