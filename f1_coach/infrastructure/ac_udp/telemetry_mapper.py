"""RTCarInfo / RTLap / HandshakerResponse → domain modeli çevirileri.

TelemetryMapper'ın (F125) AC karşılığı — UDP alan adlarını bilen tek yer
burası, domain katmanı bunlardan tamamen habersiz.
"""

from f1_coach.domain.models.ac.ac_telemetry_point import AcTelemetryPoint
from f1_coach.infrastructure.ac_udp.packets import HandshakerResponse, RTCarInfo, RTLap


def _wheel_quad(arr) -> tuple[float, float, float, float]:
    return (float(arr[0]), float(arr[1]), float(arr[2]), float(arr[3]))


def _decode_c_string(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").rstrip("\x00")


def map_handshake_info(response: HandshakerResponse) -> tuple[str, str, str, str]:
    """(car_name, driver_name, track_name, track_config) döner."""
    return (
        _decode_c_string(response.carName),
        _decode_c_string(response.driverName),
        _decode_c_string(response.trackName),
        _decode_c_string(response.trackConfig),
    )


def map_ac_telemetry_point(info: RTCarInfo, timestamp: float) -> AcTelemetryPoint:
    """RTCarInfo struct'ını AcTelemetryPoint domain modeline çevirir.

    Args:
        info:      Ham RTCarInfo struct'ı.
        timestamp: Session başlangıcından itibaren geçen saniye — struct'ın
                   kendisinde zaman damgası olmadığı için çağıran taraf
                   (AcTelemetryClient) paket alındığı anda hesaplayıp verir.
    """
    return AcTelemetryPoint(
        timestamp=timestamp,
        speed_kmh=float(info.speed_Kmh),
        speed_mph=float(info.speed_Mph),
        speed_ms=float(info.speed_Ms),
        is_abs_enabled=bool(info.isAbsEnabled),
        is_abs_in_action=bool(info.isAbsInAction),
        is_tc_enabled=bool(info.isTcEnabled),
        is_tc_in_action=bool(info.isTcInAction),
        is_in_pit=bool(info.isInPit),
        is_engine_limiter_on=bool(info.isEngineLimiterOn),
        acc_g_vertical=float(info.accG_vertical),
        acc_g_horizontal=float(info.accG_horizontal),
        acc_g_frontal=float(info.accG_frontal),
        lap_time_ms=int(info.lapTime),
        last_lap_ms=int(info.lastLap),
        best_lap_ms=int(info.bestLap),
        lap_count=int(info.lapCount),
        throttle=float(info.gas),
        brake=float(info.brake),
        clutch=float(info.clutch),
        engine_rpm=float(info.engineRPM),
        steer=float(info.steer),
        gear=int(info.gear),
        cg_height=float(info.cgHeight),
        wheel_angular_speed=_wheel_quad(info.wheelAngularSpeed),
        slip_angle=_wheel_quad(info.slipAngle),
        slip_angle_contact_patch=_wheel_quad(info.slipAngle_ContactPatch),
        slip_ratio=_wheel_quad(info.slipRatio),
        tyre_slip=_wheel_quad(info.tyreSlip),
        nd_slip=_wheel_quad(info.ndSlip),
        load=_wheel_quad(info.load),
        dy=_wheel_quad(info.Dy),
        mz=_wheel_quad(info.Mz),
        tyre_dirty_level=_wheel_quad(info.tyreDirtyLevel),
        camber_rad=_wheel_quad(info.camberRAD),
        tyre_radius=_wheel_quad(info.tyreRadius),
        tyre_loaded_radius=_wheel_quad(info.tyreLoadedRadius),
        suspension_height=_wheel_quad(info.suspensionHeight),
        car_position_normalized=float(info.carPositionNormalized),
        car_slope=float(info.carSlope),
        car_coordinates=(
            float(info.carCoordinates[0]), float(info.carCoordinates[1]), float(info.carCoordinates[2])
        ),
    )


def map_rt_lap_info(lap: RTLap) -> tuple[str, int, int]:
    """(driver_name, lap_number, lap_time_ms) döner."""
    return _decode_c_string(lap.driverName), int(lap.lap), int(lap.time)