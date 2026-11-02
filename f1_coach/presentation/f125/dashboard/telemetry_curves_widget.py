"""Live vs Ideal Telemetry Traces Widget for F1 25.

Replaces driver biometrics with live high-frequency control telemetry:
- Throttle / Acceleration (0-100%): Live vs Ideal Best Lap
- Brake Pressure (0-100%): Live vs Ideal Best Lap
- Speed & Delta (KM/H): Live Speed vs Reference Lap with real-time delta
"""

from collections import deque
import math
from pathlib import Path
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

import pandas as pd

from f1_coach.domain.models.f125.lap import Lap
from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.f125_parquet_writer import read_telemetry

logger = get_logger(__name__)


class DualOscilloscopeCanvas(QWidget):
    """Scrolling waveform canvas comparing Live trace vs Ideal Reference trace."""

    def __init__(
        self,
        live_color: QColor,
        ideal_color: QColor,
        is_area: bool = True,
        min_val: float = 0.0,
        max_val: float = 100.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(68)
        self._live_color = live_color
        self._ideal_color = ideal_color
        self._is_area = is_area
        self._min_val = min_val
        self._max_val = max_val

        self._live_buffer: deque[float] = deque([min_val] * 120, maxlen=120)
        self._ideal_buffer: deque[float] = deque([min_val] * 120, maxlen=120)

    def push_values(self, live_val: float, ideal_val: float | None = None) -> None:
        self._live_buffer.append(live_val)
        if ideal_val is not None:
            self._ideal_buffer.append(ideal_val)
        else:
            # If no ideal reference loaded yet, mirror or track baseline
            self._ideal_buffer.append(self._ideal_buffer[-1] if self._ideal_buffer else live_val)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Grid lines (25%, 50%, 75%)
        grid_pen = QPen(QColor(16, 36, 40), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        painter.drawLine(0, int(h * 0.25), w, int(h * 0.25))
        painter.drawLine(0, int(h * 0.50), w, int(h * 0.50))
        painter.drawLine(0, int(h * 0.75), w, int(h * 0.75))

        if len(self._live_buffer) < 2:
            return

        step_x = w / float(len(self._live_buffer) - 1)
        val_range = max(1.0, self._max_val - self._min_val)

        # 1. Build Ideal Reference Path (Dashed line)
        ideal_path = QPainterPath()
        first_ideal = True
        for i, val in enumerate(self._ideal_buffer):
            norm_y = (val - self._min_val) / val_range
            norm_y = max(0.0, min(1.0, norm_y))
            py = h - 4 - (norm_y * (h - 8))
            px = i * step_x
            if first_ideal:
                ideal_path.moveTo(px, py)
                first_ideal = False
            else:
                ideal_path.lineTo(px, py)

        # Draw Ideal Dashed Line
        ideal_pen = QPen(self._ideal_color, 1.5, Qt.PenStyle.DashLine)
        painter.setPen(ideal_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(ideal_path)

        # 2. Build Live Path (Solid line + Glow + Area Fill)
        live_path = QPainterPath()
        first_live = True
        for i, val in enumerate(self._live_buffer):
            norm_y = (val - self._min_val) / val_range
            norm_y = max(0.0, min(1.0, norm_y))
            py = h - 4 - (norm_y * (h - 8))
            px = i * step_x
            if first_live:
                live_path.moveTo(px, py)
                first_live = False
            else:
                live_path.lineTo(px, py)

        # Area gradient fill under live curve
        if self._is_area:
            area_path = QPainterPath(live_path)
            area_path.lineTo(w, h)
            area_path.lineTo(0, h)
            area_path.closeSubpath()

            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(self._live_color.red(), self._live_color.green(), self._live_color.blue(), 65))
            grad.setColorAt(1.0, QColor(self._live_color.red(), self._live_color.green(), self._live_color.blue(), 5))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawPath(area_path)

        # Outer soft glow for live line
        glow_pen = QPen(QColor(self._live_color.red(), self._live_color.green(), self._live_color.blue(), 80), 4)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(live_path)

        # Main crisp solid live line
        main_pen = QPen(self._live_color, 2)
        painter.setPen(main_pen)
        painter.drawPath(live_path)


class TelemetryCurveCard(QFrame):
    """Single telemetry monitor card comparing Live vs Ideal values."""

    def __init__(
        self,
        title: str,
        unit_str: str,
        live_color: QColor,
        ideal_color: QColor,
        is_area: bool = True,
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

        # Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        titles_col = QVBoxLayout()
        titles_col.setSpacing(1)
        t_label = QLabel(title)
        t_label.setStyleSheet(
            f"font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: {live_color.name()}; background: transparent;"
        )
        sub_label = QLabel(f"Live (solid) vs Ideal (dashed) · {unit_str}")
        sub_label.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        titles_col.addWidget(t_label)
        titles_col.addWidget(sub_label)
        header_row.addLayout(titles_col)

        header_row.addStretch(1)

        # Live Digital Readout Badge
        self._live_badge = QLabel("0%")
        self._live_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_badge.setFixedSize(54, 34)
        self._live_badge.setStyleSheet(
            f"QLabel {{ background-color: #0E292A; border: 1.5px solid {live_color.name()}; border-radius: 8px; "
            f"color: #E6F4F1; font-size: 13px; font-weight: 900; }}"
        )
        header_row.addWidget(self._live_badge)

        # Ideal Comparison Column
        comp_col = QVBoxLayout()
        comp_col.setSpacing(1)
        self._ideal_label = QLabel("Ideal: —")
        self._ideal_label.setStyleSheet(f"font-size: 9px; font-weight: 700; color: {ideal_color.name()}; background: transparent;")
        self._delta_label = QLabel("Δ: 0.0%")
        self._delta_label.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        comp_col.addWidget(self._ideal_label)
        comp_col.addWidget(self._delta_label)
        header_row.addLayout(comp_col)

        layout.addLayout(header_row)

        # Waveform Canvas
        self._canvas = DualOscilloscopeCanvas(
            live_color=live_color,
            ideal_color=ideal_color,
            is_area=is_area,
            min_val=min_val,
            max_val=max_val,
        )
        layout.addWidget(self._canvas)

    def update_metrics(self, live_val: float, ideal_val: float | None, unit: str = "%") -> None:
        if unit == "%":
            self._live_badge.setText(f"{int(live_val)}%")
        else:
            self._live_badge.setText(f"{int(live_val)}")

        if ideal_val is not None:
            if unit == "%":
                self._ideal_label.setText(f"Ideal: {int(ideal_val)}%")
                delta = live_val - ideal_val
                delta_sign = "+" if delta > 0 else ""
                self._delta_label.setText(f"Δ: {delta_sign}{delta:.1f}%")
            else:
                self._ideal_label.setText(f"Ideal: {int(ideal_val)} {unit}")
                delta = live_val - ideal_val
                delta_sign = "+" if delta > 0 else ""
                self._delta_label.setText(f"Δ: {delta_sign}{int(delta)} {unit}")
        else:
            self._ideal_label.setText("Ideal: Lap 1...")
            self._delta_label.setText("Δ: Recording")

        self._canvas.push_values(live_val, ideal_val)


class TelemetryCurvesWidget(QWidget):
    """Right-column console showing live vs ideal telemetry traces."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Throttle / Acceleration (Live Teal vs Ideal Purple)
        self._throttle_card = TelemetryCurveCard(
            title="⚡ THROTTLE & ACCEL",
            unit_str="0-100%",
            live_color=QColor(0, 210, 190),       # Petronas Teal
            ideal_color=QColor(168, 85, 247),     # Purple Reference
            is_area=True,
            min_val=0.0,
            max_val=100.0,
        )
        layout.addWidget(self._throttle_card)

        # 2. Braking Force (Live Crimson vs Ideal Amber)
        self._brake_card = TelemetryCurveCard(
            title="🛑 BRAKING FORCE",
            unit_str="0-100%",
            live_color=QColor(239, 68, 68),       # Crimson Red
            ideal_color=QColor(245, 158, 11),     # Amber Reference
            is_area=True,
            min_val=0.0,
            max_val=100.0,
        )
        layout.addWidget(self._brake_card)

        # 3. Speed & Delta Trace (Live Cyan vs Ideal Green)
        self._speed_card = TelemetryCurveCard(
            title="📈 SPEED & DELTA",
            unit_str="KM/H",
            live_color=QColor(56, 189, 248),      # Cyan
            ideal_color=QColor(34, 197, 94),      # Green Reference
            is_area=True,
            min_val=0.0,
            max_val=350.0,
        )
        layout.addWidget(self._speed_card)

        # Cached reference telemetry dataframe from best lap
        self._reference_df: pd.DataFrame | None = None
        self._loaded_ref_lap_id: int | None = None

    def set_reference_lap(self, lap: Lap | None) -> None:
        """Loads and caches reference telemetry points from the best lap."""
        if lap is None or not lap.telemetry_file or not Path(lap.telemetry_file).exists():
            self._reference_df = None
            self._loaded_ref_lap_id = None
            return

        if self._loaded_ref_lap_id == lap.lap_number and self._reference_df is not None:
            return

        try:
            df = read_telemetry(lap.telemetry_file)
            if not df.empty and "track_position" in df.columns:
                self._reference_df = df.sort_values("track_position").reset_index(drop=True)
                self._loaded_ref_lap_id = lap.lap_number
                logger.info("Loaded reference telemetry for Pit Wall: lap %d (%d pts)", lap.lap_number, len(df))
        except Exception as exc:
            logger.warning("Could not read reference telemetry from %s: %s", lap.telemetry_file, exc)
            self._reference_df = None

    def tick(self, snapshot: LiveTelemetrySnapshot) -> None:
        """Sample ideal values at the current track position and update waveforms."""
        live_throttle = snapshot.throttle * 100.0
        live_brake = snapshot.brake * 100.0
        live_speed = float(snapshot.speed_kmh)

        ideal_throttle: float | None = None
        ideal_brake: float | None = None
        ideal_speed: float | None = None

        if self._reference_df is not None and not self._reference_df.empty:
            # Query the closest point on the track in the reference lap
            cur_pos = snapshot.lap_distance
            # binary search or index lookup
            idx = (self._reference_df["track_position"] - cur_pos).abs().idxmin()
            ref_row = self._reference_df.iloc[idx]
            ideal_throttle = float(ref_row.get("throttle", 0.0)) * 100.0
            ideal_brake = float(ref_row.get("brake", 0.0)) * 100.0
            ideal_speed = float(ref_row.get("speed", 0.0))
        elif snapshot.speed_kmh > 0:
            # Synthetic realistic target curve when building first lap
            phase = snapshot.lap_progress * 2 * math.pi * 8
            ideal_throttle = max(0.0, min(100.0, 50.0 + 45.0 * math.cos(phase)))
            ideal_brake = max(0.0, min(100.0, 70.0 * math.sin(phase))) if math.sin(phase) > 0.4 else 0.0
            ideal_speed = max(80.0, min(330.0, 220.0 + 80.0 * math.sin(phase + 1)))

        self._throttle_card.update_metrics(live_throttle, ideal_throttle, unit="%")
        self._brake_card.update_metrics(live_brake, ideal_brake, unit="%")
        self._speed_card.update_metrics(live_speed, ideal_speed, unit="KM/H")
