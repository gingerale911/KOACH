"""Assetto Corsa UDP paket parser'ları.

F125'in packet_parsers.py'siyle aynı desen: hatalı/kısa veri gelirse
None döner, capture loop'un çökmesini önler.
"""

import ctypes

from f1_coach.infrastructure.ac_udp.packets import HandshakerResponse, RTCarInfo, RTLap
from f1_coach.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def _parse(struct_type: type, data: bytes):
    expected = ctypes.sizeof(struct_type)
    if len(data) < expected:
        logger.debug(
            "AC packet too short: got %d bytes, expected %d for %s",
            len(data), expected, struct_type.__name__,
        )
        return None
    try:
        return struct_type.from_buffer_copy(data)
    except Exception as exc:
        logger.debug("AC parse error for %s: %s", struct_type.__name__, exc)
        return None


def parse_handshake_response(data: bytes) -> HandshakerResponse | None:
    return _parse(HandshakerResponse, data)


def parse_rt_car_info(data: bytes) -> RTCarInfo | None:
    return _parse(RTCarInfo, data)


def parse_rt_lap(data: bytes) -> RTLap | None:
    return _parse(RTLap, data)