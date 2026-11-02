"""Live track map: circuit outline, racing line and the car's position."""

import math
from collections.abc import Callable

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from f1_coach.presentation.f125.dashboard.track_outline import (
    Point,
    TrackOutline,
    load_track_outline,
)

_EDGE_COLOR = QColor(0, 210, 190, 210)
_SURFACE_COLOR = QColor(0, 210, 190, 30)
_RACING_LINE_COLOR = QColor(230, 244, 241, 80)
_CAR_BEACON_COLOR = QColor(0, 210, 190, 70)
_CAR_COLOR = QColor(255, 255, 255)
_MUTED_TEXT_COLOR = QColor(140, 165, 162)
_ATTRIBUTION = "Track map: ShfonicDashTracks (CC BY 4.0)"
_MARGIN = 18.0
_LABEL_HEIGHT = 16.0

_ToScreen = Callable[[float, float], QPointF]


def _rotate(points: tuple[Point, ...], cos_a: float, sin_a: float) -> list[Point]:
    return [(x * cos_a - z * sin_a, x * sin_a + z * cos_a) for x, z in points]


class TrackMapCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._track_id: int | None = None
        self._outline: TrackOutline | None = None
        self._car: Point | None = None

    def set_track_state(self, track_id: int, car_x: float, car_z: float) -> None:
        if track_id != self._track_id:
            self._track_id = track_id
            self._outline = load_track_outline(track_id)
        self._car = (car_x, car_z)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._outline is None:
            self._paint_unavailable(painter)
        else:
            self._paint_outline(painter, self._outline)
        painter.end()

    def _paint_unavailable(self, painter: QPainter) -> None:
        painter.setPen(_MUTED_TEXT_COLOR)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Track map unavailable")

    def _paint_outline(self, painter: QPainter, outline: TrackOutline) -> None:
        angle = math.radians(outline.orientation_deg)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        left = _rotate(outline.left_edge, cos_a, sin_a)
        right = _rotate(outline.right_edge, cos_a, sin_a)
        line = _rotate(outline.racing_line, cos_a, sin_a)

        all_points = left + right
        min_x = min(x for x, _ in all_points)
        max_x = max(x for x, _ in all_points)
        min_z = min(z for _, z in all_points)
        max_z = max(z for _, z in all_points)
        avail_w = self.width() - 2 * _MARGIN
        avail_h = self.height() - 2 * _MARGIN - _LABEL_HEIGHT
        span_x = max(max_x - min_x, 1e-6)
        span_z = max(max_z - min_z, 1e-6)
        scale = min(avail_w / span_x, avail_h / span_z)
        offset_x = _MARGIN + (avail_w - span_x * scale) / 2
        offset_z = _MARGIN + (avail_h - span_z * scale) / 2

        def to_screen(x: float, z: float) -> QPointF:
            return QPointF(
                offset_x + (x - min_x) * scale,
                offset_z + (z - min_z) * scale,
            )

        surface = self._polygon_path(left, right, to_screen)
        painter.fillPath(surface, _SURFACE_COLOR)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_EDGE_COLOR, 1.5))
        painter.drawPath(self._closed_path(left, to_screen))
        painter.drawPath(self._closed_path(right, to_screen))

        painter.setPen(QPen(_RACING_LINE_COLOR, 1))
        painter.drawPath(self._closed_path(line, to_screen))

        if self._car is not None:
            car_x, car_z = self._car
            car_point = _rotate(((car_x, car_z),), cos_a, sin_a)[0]
            car_screen = to_screen(*car_point)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_CAR_BEACON_COLOR)
            painter.drawEllipse(car_screen, 9, 9)
            painter.setBrush(_CAR_COLOR)
            painter.setPen(QPen(_EDGE_COLOR, 2))
            painter.drawEllipse(car_screen, 4.5, 4.5)

        self._paint_attribution(painter)

    @staticmethod
    def _closed_path(points: list[Point], to_screen: _ToScreen) -> QPainterPath:
        path = QPainterPath()
        first = to_screen(*points[0])
        path.moveTo(first)
        for x, z in points[1:]:
            path.lineTo(to_screen(x, z))
        path.closeSubpath()
        return path

    def _polygon_path(self, left: list[Point], right: list[Point], to_screen: _ToScreen) -> QPainterPath:
        path = self._closed_path(left, to_screen)
        for x, z in reversed(right):
            path.lineTo(to_screen(x, z))
        path.closeSubpath()
        return path

    def _paint_attribution(self, painter: QPainter) -> None:
        font = QFont()
        font.setPointSizeF(7.0)
        painter.setFont(font)
        painter.setPen(_MUTED_TEXT_COLOR)
        label_rect = self.rect().adjusted(8, 0, -8, -4)
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            _ATTRIBUTION,
        )
