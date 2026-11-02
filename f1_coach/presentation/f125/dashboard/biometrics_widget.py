"""Driver Biometrics & Real-Time Waveform Oscilloscopes Widget.

Renders animated medical-grade telemetry waveforms for:
- Heart Rate (BPM) with dynamic ECG cardiac trace and min/max metrics
- Breaths Per Minute with smooth respiratory sinusoidal curve
- Physical Driver Stress Level (0-100) combining 3-axis G-forces
"""

from collections import deque
import math
import time
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot


class OscilloscopeCanvas(QWidget):
    """Real-time scrolling waveform canvas."""

    def __init__(
        self,
        line_color: QColor,
        is_ecg: bool = False,
        is_area: bool = False,
        min_val: float = 0.0,
        max_val: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(64)
        self._line_color = line_color
        self._is_ecg = is_ecg
        self._is_area = is_area
        self._min_val = min_val
        self._max_val = max_val

        self._buffer: deque[float] = deque([min_val] * 120, maxlen=120)
        self._phase: float = 0.0

    def push_value(self, val: float) -> None:
        self._buffer.append(val)
        self.update()

    def advance_ecg(self, current_bpm: float) -> None:
        """Simulate realistic P-Q-R-S-T ECG cardiac waveform based on BPM."""
        self._phase += (current_bpm / 60.0) * 0.18
        cycle = self._phase % (2 * math.pi)

        # Baseline
        val = 0.0
        # P wave
        if 0.5 < cycle < 1.0:
            val = math.sin((cycle - 0.5) * 2 * math.pi) * 0.15
        # Q dip
        elif 1.4 < cycle < 1.6:
            val = -0.25
        # R spike
        elif 1.6 <= cycle <= 1.8:
            val = 1.0
        # S dip
        elif 1.8 < cycle < 2.0:
            val = -0.35
        # T wave
        elif 2.4 < cycle < 3.2:
            val = math.sin((cycle - 2.4) * (math.pi / 0.8)) * 0.25

        # Normalize to BPM range
        bpm_val = current_bpm + (val * 40.0)
        self.push_value(bpm_val)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Grid lines
        grid_pen = QPen(QColor(16, 36, 40), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        painter.drawLine(0, int(h * 0.25), w, int(h * 0.25))
        painter.drawLine(0, int(h * 0.50), w, int(h * 0.50))
        painter.drawLine(0, int(h * 0.75), w, int(h * 0.75))

        if len(self._buffer) < 2:
            return

        # Compute waveform path
        step_x = w / float(len(self._buffer) - 1)
        val_range = max(1.0, self._max_val - self._min_val)

        path = QPainterPath()
        first = True

        for i, val in enumerate(self._buffer):
            norm_y = (val - self._min_val) / val_range
            norm_y = max(0.0, min(1.0, norm_y))
            py = h - 4 - (norm_y * (h - 8))
            px = i * step_x

            if first:
                path.moveTo(px, py)
                first = False
            else:
                path.lineTo(px, py)

        # Draw area under curve if requested
        if self._is_area:
            area_path = QPainterPath(path)
            area_path.lineTo(w, h)
            area_path.lineTo(0, h)
            area_path.closeSubpath()

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(self._line_color.red(), self._line_color.green(), self._line_color.blue(), 70))
            grad.setColorAt(1.0, QColor(self._line_color.red(), self._line_color.green(), self._line_color.blue(), 5))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawPath(area_path)

        # Draw main glow & line
        glow_pen = QPen(QColor(self._line_color.red(), self._line_color.green(), self._line_color.blue(), 80), 4)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        line_pen = QPen(self._line_color, 2)
        painter.setPen(line_pen)
        painter.drawPath(path)


class BiometricCard(QFrame):
    """Single biometric monitor card containing title, waveform, and digital badge."""

    def __init__(
        self,
        title: str,
        range_str: str,
        color: QColor,
        is_ecg: bool = False,
        is_area: bool = False,
        min_val: float = 0.0,
        max_val: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #0B1618; border: 1px solid #14282B; border-radius: 12px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Top Header & Badge Row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        titles_col = QVBoxLayout()
        titles_col.setSpacing(1)
        t_label = QLabel(title)
        t_label.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1.5px; color: #00D2BE; background: transparent;")
        r_label = QLabel(range_str)
        r_label.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        titles_col.addWidget(t_label)
        titles_col.addWidget(r_label)
        header_row.addLayout(titles_col)

        header_row.addStretch(1)

        # Round Badge
        self._badge = QLabel("65")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedSize(38, 38)
        self._badge.setStyleSheet(
            f"QLabel {{ background-color: #0E292A; border: 1.5px solid {color.name()}; border-radius: 19px; "
            f"color: #E6F4F1; font-size: 14px; font-weight: 900; }}"
        )
        header_row.addWidget(self._badge)

        # Highest / Lowest Stats
        stats_col = QVBoxLayout()
        stats_col.setSpacing(1)
        self._high_label = QLabel("High: 130")
        self._high_label.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        self._low_label = QLabel("Low: 48")
        self._low_label.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        stats_col.addWidget(self._high_label)
        stats_col.addWidget(self._low_label)
        header_row.addLayout(stats_col)

        layout.addLayout(header_row)

        # Waveform Canvas
        self._canvas = OscilloscopeCanvas(
            line_color=color,
            is_ecg=is_ecg,
            is_area=is_area,
            min_val=min_val,
            max_val=max_val,
        )
        layout.addWidget(self._canvas)

    def update_badge(self, current: int, highest: int, lowest: int) -> None:
        self._badge.setText(str(current))
        self._high_label.setText(f"High: {highest}")
        self._low_label.setText(f"Low: {lowest}")


class DriverBiometricsWidget(QWidget):
    """Right-side column housing Heart Rate, Breaths, and Stress waveforms."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Heart Rate (ECG)
        self._hr_card = BiometricCard(
            title="❤️ HEART RATE",
            range_str="(40-200 BPM)",
            color=QColor(0, 210, 190),
            is_ecg=True,
            is_area=False,
            min_val=40,
            max_val=200,
        )
        layout.addWidget(self._hr_card)

        # 2. Breaths Per Minute
        self._breaths_card = BiometricCard(
            title="🫁 BREATHS PER MINUTE",
            range_str="(0-25)",
            color=QColor(56, 189, 248),
            is_ecg=False,
            is_area=True,
            min_val=0,
            max_val=25,
        )
        layout.addWidget(self._breaths_card)

        # 3. Stress Level
        self._stress_card = BiometricCard(
            title="⚡ STRESS LEVEL",
            range_str="(0-100)",
            color=QColor(249, 115, 22),
            is_ecg=False,
            is_area=True,
            min_val=0,
            max_val=100,
        )
        layout.addWidget(self._stress_card)

        # Biometric running min/max stats
        self._max_hr = 72
        self._min_hr = 65
        self._max_br = 14
        self._min_br = 12
        self._max_stress = 50
        self._min_stress = 40
        self._breath_phase = 0.0

    def tick(self, snapshot: LiveTelemetrySnapshot, cur_time: float) -> None:
        # 1. Heart rate
        hr = snapshot.calculate_heart_rate(cur_time)
        self._max_hr = max(self._max_hr, hr)
        self._min_hr = min(self._min_hr, hr)
        self._hr_card.update_badge(hr, self._max_hr, self._min_hr)
        self._hr_card._canvas.advance_ecg(hr)

        # 2. Breaths
        br = snapshot.calculate_respiration_rate()
        self._max_br = max(self._max_br, br)
        self._min_br = min(self._min_br, br)
        self._breaths_card.update_badge(br, self._max_br, self._min_br)

        self._breath_phase += (br / 60.0) * 0.25
        wave_br = br + math.sin(self._breath_phase) * 3.5
        self._breaths_card._canvas.push_value(wave_br)

        # 3. Stress level
        stress = snapshot.calculate_driver_stress()
        st_int = int(stress)
        self._max_stress = max(self._max_stress, st_int)
        self._min_stress = min(self._min_stress, st_int)
        self._stress_card.update_badge(st_int, self._max_stress, self._min_stress)
        self._stress_card._canvas.push_value(stress)
