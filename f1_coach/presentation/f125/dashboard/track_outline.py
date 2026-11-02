"""Circuit outlines for F1 25 tracks, sourced from ShfonicDashTracks (CC BY 4.0)."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_TRACK_DATA_DIR = Path(__file__).parent / "track_data"

_TRACK_FILES: dict[int, str] = {
    0: "f1-25_melbourne.json",
    2: "f1-25_shanghai.json",
    3: "f1-25_sakhir.json",
    7: "f1-25_silverstone.json",
    9: "f1-25_hungaroring.json",
    10: "f1-25_spa.json",
    11: "f1-25_monza.json",
    12: "f1-25_singapore.json",
    13: "f1-25_suzuka.json",
    14: "f1-25_abu-dhabi.json",
    17: "f1-25_red-bull-ring.json",
    20: "f1-25_baku.json",
    26: "f1-25_zandvoort.json",
    27: "f1-25_imola.json",
}

Point = tuple[float, float]


@dataclass(frozen=True)
class TrackOutline:
    left_edge: tuple[Point, ...]
    right_edge: tuple[Point, ...]
    racing_line: tuple[Point, ...]
    orientation_deg: float


def _points(raw: list[list[float]]) -> tuple[Point, ...]:
    return tuple((float(x), float(z)) for x, z in raw)


@lru_cache(maxsize=None)
def load_track_outline(track_id: int) -> TrackOutline | None:
    file_name = _TRACK_FILES.get(track_id)
    if file_name is None:
        return None
    with (_TRACK_DATA_DIR / file_name).open(encoding="utf-8") as fh:
        data = json.load(fh)
    return TrackOutline(
        left_edge=_points(data["left_edge"]),
        right_edge=_points(data["right_edge"]),
        racing_line=_points(data["lines"]["formula1"]["racing_line"]),
        orientation_deg=float(data.get("orientation", 0.0)),
    )
