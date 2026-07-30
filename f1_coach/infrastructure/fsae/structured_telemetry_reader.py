"""structured_telemetry_reader.py — JSON/XLSX telemetri dosyalarını
VehicleTelemetryPoint listesine çevirir.

CAN etiketleme akışına ALTERNATİF bir yol: hâlihazırda yapılandırılmış
(kendi araç yazılımlarından dışa aktarılmış) telemetri verisi olan
takımlar, ham CAN log + manuel etiketleme sürecinden geçmeden doğrudan
bir VehicleSession oluşturabilir.

Desteklenen iki dosya şekli, otomatik algılanır:
    - "Uzun" (long) format: timestamp, channel_name, value sütunları
    - "Geniş" (wide) format: bir zaman sütunu + kanal başına bir sütun,
      pivot edilerek uzun formata çevrilir

Zaman sütunu adı esnek tutuldu: "timestamp", "time", "zaman" (büyük/küçük
harf duyarsız) — bunlardan biri bulunamazsa dosya işlenemez.
"""

from pathlib import Path

import pandas as pd

from f1_coach.domain.models.fsae.vehicle_telemetry_point import VehicleTelemetryPoint
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_TIMESTAMP_COLUMN_ALIASES = {"timestamp", "time", "zaman"}
_LONG_FORMAT_VALUE_ALIASES = {"value", "deger", "değer"}
_LONG_FORMAT_CHANNEL_ALIASES = {"channel_name", "channel", "kanal", "kanal_adi", "kanal_adı"}


def _find_column(df: pd.DataFrame, aliases: set[str]) -> str | None:
    """Sütun isimlerini büyük/küçük harf duyarsız eşleştirip gerçek sütun adını döner."""
    lowered = {str(col).lower().strip(): col for col in df.columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def _normalize_to_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """Bir DataFrame'i (uzun ya da geniş formatta) standart uzun formata çevirir.

    Returns:
        Yalnızca "timestamp", "channel_name", "value" sütunlarını içeren DataFrame.

    Raises:
        ValueError: Zaman sütunu bulunamazsa.
    """
    timestamp_col = _find_column(df, _TIMESTAMP_COLUMN_ALIASES)
    if timestamp_col is None:
        raise ValueError(
            "Dosyada zaman sütunu bulunamadı — sütunlardan biri "
            "'timestamp', 'time' ya da 'zaman' olmalı."
        )

    channel_col = _find_column(df, _LONG_FORMAT_CHANNEL_ALIASES)
    value_col = _find_column(df, _LONG_FORMAT_VALUE_ALIASES)

    if channel_col is not None and value_col is not None:
        logger.debug("Dosya uzun (long) format olarak algılandı.")
        result = df[[timestamp_col, channel_col, value_col]].copy()
        result.columns = ["timestamp", "channel_name", "value"]
        return result

    logger.debug("Dosya geniş (wide) format olarak algılandı, uzun formata çevriliyor.")
    channel_columns = [col for col in df.columns if col != timestamp_col]
    if not channel_columns:
        raise ValueError("Zaman sütunu dışında hiçbir kanal sütunu bulunamadı.")

    melted = df.melt(
        id_vars=[timestamp_col], value_vars=channel_columns,
        var_name="channel_name", value_name="value",
    )
    melted = melted.rename(columns={timestamp_col: "timestamp"})
    return melted[["timestamp", "channel_name", "value"]]


def _dataframe_to_points(df: pd.DataFrame) -> list[VehicleTelemetryPoint]:
    df = df.dropna(subset=["timestamp", "value"])
    return [
        VehicleTelemetryPoint(
            timestamp=float(row.timestamp),
            channel_name=str(row.channel_name),
            value=float(row.value),
        )
        for row in df.itertuples(index=False)
    ]


def read_structured_telemetry(file_path: str) -> list[VehicleTelemetryPoint]:
    """JSON ya da XLSX dosyasını okuyup VehicleTelemetryPoint listesine çevirir.

    Args:
        file_path: .json, .xlsx ya da .xls uzantılı dosya yolu.

    Returns:
        Decode edilmiş telemetri noktaları (long format).

    Raises:
        ValueError: Uzantı desteklenmiyorsa, zaman sütunu bulunamazsa,
                   ya da dosya boşsa/geçerli veri içermiyorsa.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".json":
        raw_df = pd.read_json(file_path)
    elif suffix in (".xlsx", ".xls"):
        raw_df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Desteklenmeyen dosya uzantısı: '{suffix}' (yalnızca .json/.xlsx/.xls).")

    if raw_df.empty:
        raise ValueError("Dosya boş ya da okunamadı.")

    long_df = _normalize_to_long_format(raw_df)
    points = _dataframe_to_points(long_df)

    if not points:
        raise ValueError("Dosyadan hiçbir geçerli veri noktası çıkarılamadı.")

    logger.info(
        "Yapılandırılmış telemetri dosyası okundu: %s -> %d nokta, %d kanal.",
        file_path, len(points), long_df["channel_name"].nunique(),
    )
    return points