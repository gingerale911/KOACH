"""TelemetryReceiver — UDP capture loop.

Binds to UDP port 20777 and runs a blocking receive loop in a background
thread. Each datagram is parsed, mapped to domain objects, and forwarded
to SessionManager.

Thread model:
    Main thread  → starts/stops TelemetryReceiver
    Capture thread → recv loop (blocking socket, exits when _running = False)

The socket has a 1-second timeout so the loop can check _running without
blocking forever when the game is not sending data.
"""

import math
import socket
import threading
import time

from f1_coach.domain.models.f125.live_snapshot import LiveTelemetrySnapshot
from f1_coach.domain.ports.f125.car_setup_repository import CarSetupRepository
from f1_coach.domain.ports.f125.lap_repository import LapRepository
from f1_coach.domain.ports.f125.session_repository import SessionRepository
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.f125_udp.parsers.packet_parsers import (
    parse_car_setup,
    parse_car_status,
    parse_car_telemetry,
    parse_header,
    parse_lap_data,
    parse_motion,
    parse_session,
)
from f1_coach.infrastructure.f125_udp.session_manager import SessionManager
from f1_coach.infrastructure.f125_udp.telemetry_mapper import (
    map_assist_config,
    map_car_position,
    map_car_setup_fields,
    map_car_status_point,
    map_lap_distance,
    map_lap_validity,
    map_sector_times,
    map_session_conditions,
    map_session_info,
    map_telemetry_point,
)

logger = get_logger(__name__)

_UDP_IP = "0.0.0.0"
_UDP_PORT = 20777
_BUFFER_SIZE = 2048
_SOCKET_TIMEOUT = 1.0  # seconds — allows the loop to check _running


def _normalise_pedal(value: float) -> float:
    """Clamp pedal values into the valid 0.0–1.0 range used by the domain."""
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


class TelemetryReceiver:
    """Receives F1 25 UDP telemetry and forwards parsed data to SessionManager."""

    def __init__(
        self,
        session_repo: SessionRepository,
        lap_repo: LapRepository,
        car_setup_repo: CarSetupRepository
    ) -> None:
        self._manager = SessionManager(session_repo, lap_repo, car_setup_repo)
        self._running = False
        self._thread: threading.Thread | None = None

        # Latest track position from the most recent Lap Data packet.
        # Shared between packet handlers within the same thread — no lock needed.
        self._track_position: float = 0.0
        self._track_length: float = 0.0
        self._player_index: int = 0
        self._tyre_compound: int = 16   # default: C1
        self._last_packet_time: float | None = None
        self._snapshot = LiveTelemetrySnapshot()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def live_snapshot(self) -> LiveTelemetrySnapshot:
        return self._snapshot

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def session_manager(self) -> SessionManager:
        return self._manager

    def seconds_since_last_packet(self) -> float | None:
        """Return seconds since the last UDP datagram was received.

        Returns None if no packet has ever been received in this run.
        Used by the caller to detect a stalled/disconnected telemetry feed
        (e.g. game closed or UDP toggled off) without guessing based on
        stale in-memory state.
        """
        if self._last_packet_time is None:
            return None
        return time.monotonic() - self._last_packet_time

    def start(self) -> None:
        """Start the UDP capture thread."""
        if self._running:
            logger.warning("TelemetryReceiver already running.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="TelemetryCapture",
            daemon=True,
        )
        self._thread.start()
        logger.info("TelemetryReceiver started on port %d.", _UDP_PORT)

    def stop(self) -> None:
        """Signal the capture thread to stop and wait for it to exit."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._manager.end_session()
        logger.info("TelemetryReceiver stopped.")

    # ------------------------------------------------------------------
    # Capture loop (runs in background thread)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(_SOCKET_TIMEOUT)

        try:
            sock.bind((_UDP_IP, _UDP_PORT))
            logger.info("UDP socket bound to %s:%d", _UDP_IP, _UDP_PORT)

            while self._running:
                try:
                    data, _ = sock.recvfrom(_BUFFER_SIZE)
                except TimeoutError:
                    continue  # no data yet — check _running and loop

                self._dispatch(data)

        except OSError as exc:
            logger.error("UDP socket error: %s", exc)
        finally:
            sock.close()

    def _dispatch(self, data: bytes) -> None:
        """Route a raw UDP datagram to the appropriate handler."""
        header = parse_header(data)
        if header is None:
            return

        self._last_packet_time = time.monotonic()
        self._player_index = header.m_playerCarIndex
        packet_id = header.m_packetId

        if packet_id == 0:
            self._handle_motion(data)
        elif packet_id == 1:
            self._handle_session(data)
        elif packet_id == 2:
            self._handle_lap(data, header)
        elif packet_id == 5:                      # ← yeni
            self._handle_car_setup(data)
        elif packet_id == 6:
            self._handle_telemetry(data, header)
        elif packet_id == 7:
            self._handle_car_status(data, header)
        # All other packet IDs are silently ignored

    # ------------------------------------------------------------------
    # Per-packet handlers
    # ------------------------------------------------------------------

    def _handle_motion(self, data: bytes) -> None:
        packet = parse_motion(data)
        if packet is None:
            return
        car = packet.m_carMotionData[self._player_index]
        x, z = map_car_position(car)
        self._manager.on_car_position(x, z, self._track_position)

        self._snapshot.g_force_lateral = float(car.m_gForceLateral)
        self._snapshot.g_force_longitudinal = float(car.m_gForceLongitudinal)
        self._snapshot.g_force_vertical = float(car.m_gForceVertical)
        self._snapshot.world_x = float(car.m_worldPositionX)
        self._snapshot.world_z = float(car.m_worldPositionZ)
        self._snapshot.last_packet_timestamp = time.monotonic()
    
    def _handle_session(self, data: bytes) -> None:
        packet = parse_session(data)
        if packet is None:
            return
        uid, track, session_type = map_session_info(packet)
        self._track_length = float(packet.m_trackLength)
        assist_config = map_assist_config(packet)
        self._manager.on_session_packet(
            uid, track, session_type, self._track_length, assist_config
        )
        self._manager.on_session_conditions(map_session_conditions(packet))

        self._snapshot.track_id = int(packet.m_trackId)
        self._snapshot.track_name = track.display_name
        self._snapshot.session_type_name = session_type.display_name
        self._snapshot.total_laps = int(packet.m_totalLaps)
        self._snapshot.track_length = self._track_length
        self._snapshot.air_temperature = int(packet.m_airTemperature)
        self._snapshot.track_temperature = int(packet.m_trackTemperature)
        self._snapshot.weather_name = str(session_type.display_name)
        self._snapshot.last_packet_timestamp = time.monotonic()

    def _handle_lap(self, data: bytes, header) -> None:
        packet = parse_lap_data(data)
        if packet is None:
            return
        car = packet.m_lapData[self._player_index]
        self._track_position = map_lap_distance(car, self._track_length)
        self._tyre_compound = 16  # updated by car status; use last known value here
        sector_times = map_sector_times(car)
        is_valid = map_lap_validity(car)
        self._manager.on_lap_packet(
            lap_number=int(car.m_currentLapNum),
            lap_time_ms=int(car.m_lastLapTimeInMS),
            sector_times=sector_times,
            is_valid=is_valid,
            tyre_compound=self._tyre_compound,
        )

        self._snapshot.car_position = max(1, int(car.m_carPosition))
        self._snapshot.current_lap_num = int(car.m_currentLapNum)
        self._snapshot.current_lap_time_ms = int(car.m_currentLapTimeInMS)
        self._snapshot.last_lap_time_ms = int(car.m_lastLapTimeInMS)
        self._snapshot.lap_distance = float(car.m_lapDistance)
        self._snapshot.delta_to_front_ms = int(car.m_deltaToCarInFrontInMS)
        if int(car.m_lastLapTimeInMS) > 0:
            if self._snapshot.best_lap_time_ms == 0 or int(car.m_lastLapTimeInMS) < self._snapshot.best_lap_time_ms:
                self._snapshot.best_lap_time_ms = int(car.m_lastLapTimeInMS)
        self._snapshot.last_packet_timestamp = time.monotonic()

    def _handle_telemetry(self, data: bytes, header) -> None:
        packet = parse_car_telemetry(data)
        if packet is None:
            return
        car = packet.m_carTelemetryData[self._player_index]
        point = map_telemetry_point(header, car, self._track_position)
        self._manager.on_telemetry_point(point)

        speed = int(car.m_speed)
        self._snapshot.speed_kmh = speed
        if speed > self._snapshot.max_speed_kmh:
            self._snapshot.max_speed_kmh = speed
        self._snapshot.gear = int(car.m_gear)
        self._snapshot.engine_rpm = int(car.m_engineRPM)
        self._snapshot.throttle = _normalise_pedal(float(car.m_throttle))
        self._snapshot.steer = float(car.m_steer)
        self._snapshot.brake = _normalise_pedal(float(car.m_brake))
        self._snapshot.drs_active = bool(car.m_drs == 1)
        self._snapshot.engine_temperature = int(car.m_engineTemperature)
        self._snapshot.tyres_surface_temp = (
            int(car.m_tyresSurfaceTemperature[0]),
            int(car.m_tyresSurfaceTemperature[1]),
            int(car.m_tyresSurfaceTemperature[2]),
            int(car.m_tyresSurfaceTemperature[3]),
        )
        self._snapshot.tyres_inner_temp = (
            int(car.m_tyresInnerTemperature[0]),
            int(car.m_tyresInnerTemperature[1]),
            int(car.m_tyresInnerTemperature[2]),
            int(car.m_tyresInnerTemperature[3]),
        )
        self._snapshot.tyres_pressure_psi = (
            float(car.m_tyresPressure[0]),
            float(car.m_tyresPressure[1]),
            float(car.m_tyresPressure[2]),
            float(car.m_tyresPressure[3]),
        )
        self._snapshot.brakes_temperature = (
            int(car.m_brakesTemperature[0]),
            int(car.m_brakesTemperature[1]),
            int(car.m_brakesTemperature[2]),
            int(car.m_brakesTemperature[3]),
        )
        self._snapshot.last_packet_timestamp = time.monotonic()

    def _handle_car_status(self, data: bytes, header) -> None:
        packet = parse_car_status(data)
        if packet is None:
            return
        car = packet.m_carStatusData[self._player_index]
        self._tyre_compound = int(car.m_actualTyreCompound)
        point = map_car_status_point(header, car, self._track_position)
        self._manager.on_car_status_point(point)

        self._snapshot.fuel_in_tank = float(car.m_fuelInTank)
        self._snapshot.fuel_capacity = float(car.m_fuelCapacity) if car.m_fuelCapacity > 0 else 110.0
        self._snapshot.fuel_remaining_laps = float(car.m_fuelRemainingLaps)
        self._snapshot.ers_store_energy = float(car.m_ersStoreEnergy)
        if car.m_maxRPM > 0:
            self._snapshot.max_rpm = int(car.m_maxRPM)
        self._snapshot.last_packet_timestamp = time.monotonic()

    def _handle_car_setup(self, data: bytes) -> None:
        packet = parse_car_setup(data)
        if packet is None:
            return
        car = packet.m_carSetupData[self._player_index]
        fields = map_car_setup_fields(car)
        self._manager.on_car_setup_packet(fields)