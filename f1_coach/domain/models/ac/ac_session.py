"""AcSession domain model.

Bir Assetto Corsa UDP telemetri oturumu. F1 25'in Session modeline paralel,
ama araç/pist bilgisi enum değil ham string olarak tutuluyor — AC'nin UDP
handshake cevabı (handshackerResponse) bunları serbest metin olarak
gönderiyor, F1 25'teki gibi sabit bir entegre id listesi yok.

session_uid alanı F1 25'teki UDP kaynaklı UID'nin aksine bizim tarafımızda
(bağlantı anında) üretilir — AC protokolü kendi başına böyle bir kimlik
vermiyor.
"""

from dataclasses import dataclass, field
from datetime import datetime

from f1_coach.domain.models.ac.ac_lap import AcLap


@dataclass
class AcSession:
    """Bir Assetto Corsa UDP telemetri oturumu.

    Attributes:
        session_uid:    Bağlantı anında bizim ürettiğimiz benzersiz kimlik
                        (bkz. modül docstring'i) — Parquet klasör adı olarak
                        da kullanılır.
        car_name:       handshackerResponse.carName.
        driver_name:    handshackerResponse.driverName — RTLap olaylarının
                        bize mi ait olduğunu tespit etmek için de kullanılır
                        (bkz. proje kararı: carIdentifierNumber güvenilir
                        değil, driverName eşleşmesine bakılıyor).
        track_name:     handshackerResponse.trackName.
        track_config:   handshackerResponse.trackConfig.
        created_at:     Session'ın bağlantı anındaki wall-clock zamanı.
        laps:           Bu session'da tamamlanmış turlar.
        id:             Veritabanı birincil anahtarı; -1 henüz
                        kaydedilmedi demek.
    """

    session_uid: str
    car_name: str
    driver_name: str
    track_name: str
    track_config: str
    created_at: datetime = field(default_factory=datetime.now)
    laps: list[AcLap] = field(default_factory=list)
    id: int = field(default=-1)

    @property
    def lap_count(self) -> int:
        return len(self.laps)

    @property
    def best_lap(self) -> AcLap | None:
        """En hızlı tur, ya da hiç tur yoksa None.

        F125'in aksine burada is_valid/safety_car gibi bir dışlama
        kriteri yok — AC bu protokolde geçersiz tur bilgisi vermiyor.
        """
        if not self.laps:
            return None
        return min(self.laps, key=lambda lap: lap.lap_time_ms)

    @property
    def is_persisted(self) -> bool:
        return self.id != -1

    def add_lap(self, lap: AcLap) -> None:
        lap.session_id = self.id
        self.laps.append(lap)