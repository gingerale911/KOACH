"""AcTelemetryClient — Assetto Corsa Remote Telemetry UDP istemcisi.

F125'in TelemetryReceiver'ından farkı: F125 tek yönlü bir yayını
DİNLİYORDU, bu istemci ise önce SUNUCUYA paket GÖNDERMEK zorunda
(handshake + abonelik) — bu yüzden ayrı, kendine özgü bir sınıf.

Akış:
    1. connect() — soket açılır, handshake gönderilir, cevap beklenir
       (üç deneme, her biri timeout'lu)
    2. subscribe() — hem SUBSCRIBE_UPDATE hem SUBSCRIBE_SPOT gönderilir
       (ikisine birden abone olunup olunamayacağı gerçek sunucuyla
       doğrulanmalı — bkz. proje notu)
    3. start() — arka plan thread'inde dinleme döngüsü başlar, gelen
       paketler boyutlarına göre RTCarInfo/RTLap olarak ayrıştırılıp
       manager'a iletilir
    4. stop() — DISMISS gönderilir, thread durdurulur, soket kapanır

manager parametresi şu metodları sağlamalı (bir sonraki adımda yazılacak
AcSessionManager bu arayüzü karşılayacak — Protocol olarak tanımlanmadı
çünkü F125'teki SessionManager de aynı şekilde doğrudan somut sınıf
olarak enjekte ediliyor, port soyutlamasına gerek görülmedi):
    on_handshake(car_name, driver_name, track_name, track_config) -> None
    on_telemetry_point(AcTelemetryPoint) -> None
    on_lap_event(driver_name, lap_number, lap_time_ms) -> None
"""

import socket
import threading
import time

from f1_coach.infrastructure.ac_udp.packet_parsers import (
    parse_handshake_response,
    parse_rt_car_info,
    parse_rt_lap,
)
from f1_coach.infrastructure.ac_udp.packets import (
    HANDSHAKE_RESPONSE_SIZE,
    OP_DISMISS,
    OP_HANDSHAKE,
    OP_SUBSCRIBE_SPOT,
    OP_SUBSCRIBE_UPDATE,
    RTCARINFO_SIZE,
    RTLAP_SIZE,
    Handshaker,
)
from f1_coach.infrastructure.ac_udp.telemetry_mapper import (
    map_ac_telemetry_point,
    map_handshake_info,
    map_rt_lap_info,
)
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_RECV_BUFFER_SIZE = 2048
_HANDSHAKE_TIMEOUT_S = 2.0
_HANDSHAKE_ATTEMPTS = 3
_LOOP_SOCKET_TIMEOUT_S = 1.0  # dinleme döngüsünde _running kontrolü için


class AcConnectionError(Exception):
    """Handshake başarısız olduğunda (sunucu cevap vermediğinde) fırlatılır."""


class AcTelemetryClient:
    """Assetto Corsa ile UDP üzerinden handshake yapıp telemetriyi dinler."""

    def __init__(self, manager, host: str = "127.0.0.1", port: int = 9996) -> None:
        self._manager = manager
        self._host = host
        self._port = port
        self._socket: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._session_start_time: float | None = None

    def connect(self) -> None:
        """Soketi açar, handshake yapar. Başarısız olursa AcConnectionError fırlatır."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((self._host, self._port))
        self._socket.settimeout(_HANDSHAKE_TIMEOUT_S)

        handshake = Handshaker(identifier=1, version=1, operationId=OP_HANDSHAKE)

        for attempt in range(1, _HANDSHAKE_ATTEMPTS + 1):
            try:
                self._socket.send(bytes(handshake))
                data = self._socket.recv(_RECV_BUFFER_SIZE)
            except TimeoutError:
                logger.warning("AC handshake zaman aşımına uğradı (deneme %d/%d).", attempt, _HANDSHAKE_ATTEMPTS)
                continue

            response = parse_handshake_response(data)
            if response is None:
                logger.warning("AC handshake cevabı ayrıştırılamadı (deneme %d/%d).", attempt, _HANDSHAKE_ATTEMPTS)
                continue

            car_name, driver_name, track_name, track_config = map_handshake_info(response)
            logger.info(
                "AC handshake başarılı: car=%s driver=%s track=%s (%s)",
                car_name, driver_name, track_name, track_config,
            )
            self._manager.on_handshake(car_name, driver_name, track_name, track_config)
            return

        raise AcConnectionError(
            f"AC sunucusuna {_HANDSHAKE_ATTEMPTS} denemede bağlanılamadı — "
            "Assetto Corsa'nın açık ve Remote Telemetry'nin etkin olduğundan emin ol."
        )

    def subscribe(self) -> None:
        """Hem güncelleme (her fizik adımı) hem tur-bitti olaylarına abone olur."""
        assert self._socket is not None

        update_request = Handshaker(identifier=1, version=1, operationId=OP_SUBSCRIBE_UPDATE)
        self._socket.send(bytes(update_request))

        spot_request = Handshaker(identifier=1, version=1, operationId=OP_SUBSCRIBE_SPOT)
        self._socket.send(bytes(spot_request))

        logger.info("AC güncelleme + tur-bitti aboneliği gönderildi.")

    def start(self) -> None:
        """connect() + subscribe() sonrası dinleme thread'ini başlatır."""
        if self._running:
            logger.warning("AcTelemetryClient zaten çalışıyor.")
            return
        assert self._socket is not None

        self._socket.settimeout(_LOOP_SOCKET_TIMEOUT_S)
        self._session_start_time = time.monotonic()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="AcTelemetryCapture", daemon=True)
        self._thread.start()
        logger.info("AcTelemetryClient dinleme döngüsü başladı.")

    def stop(self) -> None:
        """DISMISS gönderir, thread'i durdurur, soketi kapatır."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        if self._socket is not None:
            try:
                dismiss = Handshaker(identifier=1, version=1, operationId=OP_DISMISS)
                self._socket.send(bytes(dismiss))
            except OSError:
                pass  # soket zaten kapanmış/kopmuş olabilir, sorun değil
            self._socket.close()
            self._socket = None

        logger.info("AcTelemetryClient durduruldu.")

    def _capture_loop(self) -> None:
        assert self._socket is not None
        while self._running:
            try:
                data = self._socket.recv(_RECV_BUFFER_SIZE)
            except TimeoutError:
                continue
            except OSError:
                break  # soket kapatıldı

            self._dispatch(data)

    def _dispatch(self, data: bytes) -> None:
        """Paketi boyutuna göre RTCarInfo ya da RTLap olarak ayrıştırır.

        AC protokolünde paket tipini ayıran ayrı bir tip alanı yok (RTLap'te
        hiç yok, RTCarInfo'daki 'identifier' güvenilir değil) — bu yüzden
        ayrım, iki struct'ın boyut farkına dayanıyor. Boyutlar çakışırsa
        (gerçek sunucuyla test edilene kadar bilinmiyor) bu mantığın
        güncellenmesi gerekebilir.
        """
        if len(data) >= RTCARINFO_SIZE:
            info = parse_rt_car_info(data)
            if info is not None:
                timestamp = time.monotonic() - (self._session_start_time or 0.0)
                point = map_ac_telemetry_point(info, timestamp)
                self._manager.on_telemetry_point(point)
                return

        if len(data) >= RTLAP_SIZE:
            lap = parse_rt_lap(data)
            if lap is not None:
                driver_name, lap_number, lap_time_ms = map_rt_lap_info(lap)
                self._manager.on_lap_event(driver_name, lap_number, lap_time_ms)
                return

        logger.debug("Tanınmayan boyutta AC paketi alındı: %d byte.", len(data))