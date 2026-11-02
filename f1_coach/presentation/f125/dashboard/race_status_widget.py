"""Race Status & Track Position Widget.

Displays race position, lap counter, lap times, deltas, top speed,
and a vector track map with live car position tracking.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot
from f1_coach.presentation.f125.dashboard.track_map_canvas import TrackMapCanvas


class RaceStatusWidget(QFrame):
    """Race Status panel containing position, lap count, times, and circuit map."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #0B1618; border: 1px solid #14282B; border-radius: 12px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # --- Card Header ---
        header_layout = QHBoxLayout()
        title = QLabel("🏁 RACE STATUS")
        title.setStyleSheet("font-size: 11px; font-weight: 800; letter-spacing: 1.5px; color: #00D2BE; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        self._track_name_label = QLabel("🇩🇪 HOCKENHEIM")
        self._track_name_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #E6F4F1; background: transparent;")
        header_layout.addWidget(self._track_name_label)
        layout.addLayout(header_layout)

        # --- Position & Lap row ---
        pos_row = QHBoxLayout()
        pos_row.setSpacing(12)

        self._pos_badge = QLabel("P1")
        self._pos_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pos_badge.setFixedSize(54, 44)
        self._pos_badge.setStyleSheet(
            "QLabel { background-color: #0E292A; border: 1.5px solid #00D2BE; border-radius: 8px; "
            "color: #00D2BE; font-size: 24px; font-weight: 900; }"
        )
        pos_row.addWidget(self._pos_badge)

        lap_layout = QVBoxLayout()
        lap_layout.setSpacing(0)
        lap_title = QLabel("LAP")
        lap_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #7A969B; background: transparent;")
        self._lap_count_label = QLabel("16/67")
        self._lap_count_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #E6F4F1; background: transparent;")
        lap_layout.addWidget(lap_title)
        lap_layout.addWidget(self._lap_count_label)
        pos_row.addLayout(lap_layout)
        pos_row.addStretch(1)
        layout.addLayout(pos_row)

        # --- Track Map Canvas ---
        self._track_map = TrackMapCanvas()
        layout.addWidget(self._track_map)

        # --- Bottom Timing & Speed Stats ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        # Top Speed
        speed_box = QVBoxLayout()
        speed_box.setSpacing(1)
        lbl_top = QLabel("Top Lap Speed")
        lbl_top.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        self._top_speed_label = QLabel("287 KM/H")
        self._top_speed_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #E6F4F1; background: transparent;")
        speed_box.addWidget(lbl_top)
        speed_box.addWidget(self._top_speed_label)
        stats_layout.addLayout(speed_box)

        # Current Lap
        cur_box = QVBoxLayout()
        cur_box.setSpacing(1)
        lbl_cur = QLabel("Current Lap")
        lbl_cur.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        self._current_lap_label = QLabel("1:21.520 -1.075")
        self._current_lap_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #00D2BE; background: transparent;")
        cur_box.addWidget(lbl_cur)
        cur_box.addWidget(self._current_lap_label)
        stats_layout.addLayout(cur_box)

        # Best Lap
        best_box = QVBoxLayout()
        best_box.setSpacing(1)
        lbl_best = QLabel("Best Lap")
        lbl_best.setStyleSheet("font-size: 9px; font-weight: 600; color: #7A969B; background: transparent;")
        self._best_lap_label = QLabel("1:23.050")
        self._best_lap_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #22C55E; background: transparent;")
        best_box.addWidget(lbl_best)
        best_box.addWidget(self._best_lap_label)
        stats_layout.addLayout(best_box)

        layout.addLayout(stats_layout)

    def update_snapshot(self, snapshot: LiveTelemetrySnapshot) -> None:
        self._pos_badge.setText(f"P{snapshot.car_position}")
        total = snapshot.total_laps if snapshot.total_laps > 0 else 67
        self._lap_count_label.setText(f"{snapshot.current_lap_num}/{total}")
        self._track_name_label.setText(snapshot.track_name.upper())

        top_spd = snapshot.max_speed_kmh if snapshot.max_speed_kmh > 0 else snapshot.speed_kmh
        self._top_speed_label.setText(f"{top_spd} KM/H")

        # Format current lap time
        cur_sec = snapshot.current_lap_time_ms / 1000.0
        cur_m, cur_s = divmod(cur_sec, 60)
        delta_str = f" -{snapshot.delta_to_front_ms / 1000.0:.3f}" if snapshot.delta_to_front_ms > 0 else ""
        self._current_lap_label.setText(f"{int(cur_m)}:{cur_s:06.3f}{delta_str}")

        if snapshot.best_lap_time_ms > 0:
            best_sec = snapshot.best_lap_time_ms / 1000.0
            bm, bs = divmod(best_sec, 60)
            self._best_lap_label.setText(f"{int(bm)}:{bs:06.3f}")

        self._track_map.set_track_state(snapshot.track_id, snapshot.world_x, snapshot.world_z)
