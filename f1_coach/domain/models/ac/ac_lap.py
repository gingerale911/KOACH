"""AcLap domain model.

Assetto Corsa'nın RTLap (SUBSCRIBE_SPOT) UDP olayından türetilen tamamlanmış
tur kaydı. F1 25'in Lap modelinden daha sade — bu protokol sektör süresi
bildirmiyor, yalnızca toplam tur süresi veriyor.
"""

from dataclasses import dataclass, field


@dataclass
class AcLap:
    """Bir Assetto Corsa session'ında tamamlanmış tek bir tur.

    Attributes:
        lap_number:      1-tabanlı tur numarası (RTLap'in "lap" alanı).
        lap_time_ms:      Tur süresi, milisaniye (RTLap'in "time" alanı —
                          oyunun kendi resmi ölçümü, RTCarInfo'daki
                          lapTime/lastLap alanlarından daha güvenilir kabul
                          edilir çünkü olay bazlı, örnekleme aralığına bağlı
                          değildir).
        telemetry_file:   Bu tura ait AcTelemetryPoint'lerin yazıldığı
                          Parquet dosyasının yolu. Boş string, henüz
                          yazılmadıysa.
        id:               Veritabanı birincil anahtarı; -1 henüz
                          kaydedilmedi demek.
        session_id:       Bağlı olduğu AcSession; -1 henüz atanmadı demek.
    """

    lap_number: int
    lap_time_ms: int
    telemetry_file: str = field(default="")
    id: int = field(default=-1)
    session_id: int = field(default=-1)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1