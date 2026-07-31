"""AcSessionManager — AC session/tur yaşam döngüsü yönetimi.

F125'in SessionManager'ına paralel, ama daha sade: setup takibi yok, tur
sınırları RTLap olayından geliyor (RTCarInfo'daki lapCount alanına göre
kendi başımıza tespit etmemize gerek yok — oyun bunu bize doğrudan
bildiriyor).

AcTelemetryClient'ın beklediği arayüzü (on_handshake, on_telemetry_point,
on_lap_event) implemente eder — bkz. ac_telemetry_client.py docstring'i.

RTLap olayları session'daki TÜM araçlar için gelir; bize ait olup
olmadığını handshake'te alınan driver_name ile karşılaştırarak tespit
ediyoruz (bkz. proje notu: carIdentifierNumber güvenilir referans değil).
"""

from datetime import datetime

from f1_coach.domain.models.ac.ac_lap import AcLap
from f1_coach.domain.models.ac.ac_session import AcSession
from f1_coach.domain.models.ac.ac_telemetry_point import AcTelemetryPoint
from f1_coach.domain.ports.ac.ac_lap_repository import AcLapRepository
from f1_coach.domain.ports.ac.ac_session_repository import AcSessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.ac.parquet_writer import write_ac_telemetry

logger = get_logger(__name__)


class AcSessionManager:
    """Owns the current AC session and handles lap transitions."""

    def __init__(self, session_repo: AcSessionRepository, lap_repo: AcLapRepository) -> None:
        self._session_repo = session_repo
        self._lap_repo = lap_repo

        self._session: AcSession | None = None
        self._telemetry_buffer: list[AcTelemetryPoint] = []
        self._latest_telemetry: AcTelemetryPoint | None = None
        self._current_lap_number: int = 1

    @property
    def current_session(self) -> AcSession | None:
        return self._session

    @property
    def latest_telemetry(self) -> AcTelemetryPoint | None:
        """Canlı gösterge amaçlı — en son alınan telemetri karesi."""
        return self._latest_telemetry

    def on_handshake(self, car_name: str, driver_name: str, track_name: str, track_config: str) -> None:
        """Yeni bir AC bağlantısı kurulduğunda çağrılır — yeni bir session başlatır."""
        import uuid

        self._session = AcSession(
            session_uid=uuid.uuid4().hex,
            car_name=car_name,
            driver_name=driver_name,
            track_name=track_name,
            track_config=track_config,
            created_at=datetime.now(),
        )
        self._session_repo.save(self._session)
        self._telemetry_buffer = []
        self._current_lap_number = 1

        logger.info(
            "AC session başladı: uid=%s car=%s driver=%s track=%s",
            self._session.session_uid, car_name, driver_name, track_name,
        )

    def on_telemetry_point(self, point: AcTelemetryPoint) -> None:
        """Her RTCarInfo paketinde çağrılır — buffer'a ekler."""
        self._latest_telemetry = point
        if self._session is not None:
            self._telemetry_buffer.append(point)

    def on_lap_event(self, driver_name: str, lap_number: int, lap_time_ms: int) -> None:
        """Her RTLap paketinde çağrılır — yalnızca bize ait olan turu işler.

        Session'daki diğer araçlara ait RTLap olayları (driver_name eşleşmiyorsa)
        sessizce yok sayılır.
        """
        if self._session is None:
            return
        if driver_name != self._session.driver_name:
            logger.debug("Başka bir sürücünün turu yok sayıldı: %s", driver_name)
            return
        if not self._telemetry_buffer:
            logger.warning("Tur bitti ama telemetri buffer'ı boş — kaydedilmedi.")
            return

        telemetry_path = write_ac_telemetry(
            self._session.session_uid, self._current_lap_number, self._telemetry_buffer
        )

        lap = AcLap(
            lap_number=lap_number,
            lap_time_ms=lap_time_ms,
            telemetry_file=telemetry_path,
            session_id=self._session.id,
        )
        self._lap_repo.save(lap)
        self._session.add_lap(lap)

        logger.info(
            "AC tur tamamlandı: lap=%d time_ms=%d points=%d",
            lap_number, lap_time_ms, len(self._telemetry_buffer),
        )

        self._telemetry_buffer = []
        self._current_lap_number += 1

    def end_session(self) -> None:
        """Bağlantı manuel olarak (kullanıcı tarafından) sonlandırıldığında çağrılır.

        Yarım kalan (tur bitmemiş) buffer kasıtlı olarak KAYDEDİLMEZ —
        F125'in aksine burada "force_invalid" gibi bir kavram yok, AC'de
        yarım turun süresi RTLap'ten gelmediği için anlamlı bir lap_time_ms
        üretemeyiz.
        """
        if self._telemetry_buffer:
            logger.info(
                "Session sonlandırılıyor — %d puanlık tamamlanmamış tur verisi atlanıyor.",
                len(self._telemetry_buffer),
            )
        self._telemetry_buffer = []
        self._session = None