"""Parquet writer for AC (Assetto Corsa) telemetry data.

F125'in parquet_writer.py'sindeki desenin birebir aynısı: her tur kendi
dosyasına yazılır. AcTelemetryPoint "wide" formatlı (F125'teki gibi sabit
alanlar) olduğu için FSAE'nin long-format Parquet'inden farklı, F125'e
daha yakın bir şema kullanıyor — ama tekerlek başına 4 elemanlı tuple'lar
olduğu için sütunlar ayrıştırılarak (ör. wheel_angular_speed_fl/fr/rl/rr)
yazılıyor.
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from f1_coach.domain.models.ac.ac_telemetry_point import AcTelemetryPoint
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path("data/ac_sessions")

_WHEEL_SUFFIXES = ("fl", "fr", "rl", "rr")
_WHEEL_FIELDS = (
    "wheel_angular_speed", "slip_angle", "slip_angle_contact_patch", "slip_ratio",
    "tyre_slip", "nd_slip", "load", "dy", "mz", "tyre_dirty_level",
    "camber_rad", "tyre_radius", "tyre_loaded_radius", "suspension_height",
)
_SCALAR_FIELDS = (
    "timestamp", "speed_kmh", "speed_mph", "speed_ms",
    "is_abs_enabled", "is_abs_in_action", "is_tc_enabled", "is_tc_in_action",
    "is_in_pit", "is_engine_limiter_on",
    "acc_g_vertical", "acc_g_horizontal", "acc_g_frontal",
    "lap_time_ms", "last_lap_ms", "best_lap_ms", "lap_count",
    "throttle", "brake", "clutch", "engine_rpm", "steer", "gear", "cg_height",
    "car_position_normalized", "car_slope",
)


def _lap_dir(session_uid: str) -> Path:
    path = _BASE_DIR / session_uid / "laps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_ac_telemetry(session_uid: str, lap_number: int, points: list[AcTelemetryPoint]) -> str:
    """Bir turun AcTelemetryPoint karelerini Parquet'e yazar.

    Tekerlek bazlı 4-elemanlı tuple alanları (wheel_angular_speed vb.)
    dört ayrı sütuna (ör. wheel_angular_speed_fl/_fr/_rl/_rr) açılır —
    Parquet'in doğrudan tuple sütunu desteklememesi ve düz sütunların
    grafik/analiz kodunda çalışması daha kolay olduğu için.

    Raises:
        ValueError: points boşsa.
    """
    if not points:
        raise ValueError(f"No AC telemetry points to write for lap {lap_number}.")

    data: dict[str, list] = {field: [] for field in _SCALAR_FIELDS}
    for field in _WHEEL_FIELDS:
        for suffix in _WHEEL_SUFFIXES:
            data[f"{field}_{suffix}"] = []
    data["car_coordinates_x"] = []
    data["car_coordinates_y"] = []
    data["car_coordinates_z"] = []

    for point in points:
        for field in _SCALAR_FIELDS:
            data[field].append(getattr(point, field))
        for field in _WHEEL_FIELDS:
            quad = getattr(point, field)
            for suffix, value in zip(_WHEEL_SUFFIXES, quad):
                data[f"{field}_{suffix}"].append(value)
        data["car_coordinates_x"].append(point.car_coordinates[0])
        data["car_coordinates_y"].append(point.car_coordinates[1])
        data["car_coordinates_z"].append(point.car_coordinates[2])

    df = pd.DataFrame(data)
    output_path = _lap_dir(session_uid) / f"lap_{lap_number:03d}_telemetry.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")

    logger.debug("AC telemetry written: session=%s lap=%d rows=%d path=%s", session_uid, lap_number, len(points), output_path)
    return str(output_path.resolve())


def read_ac_telemetry(file_path: str) -> pd.DataFrame:
    """Bir AC tur Parquet dosyasını DataFrame olarak okur."""
    return pq.read_table(file_path).to_pandas()


def delete_ac_session_files(session_uid: str) -> None:
    """Session'a ait tüm Parquet dosyalarını diskten siler."""
    import shutil

    session_dir = _BASE_DIR / session_uid
    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.info("Deleted AC session directory: %s", session_dir)