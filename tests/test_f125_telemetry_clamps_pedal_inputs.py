from f1_coach.infrastructure.f125_udp.packets import CarTelemetryData, PacketHeader
from f1_coach.infrastructure.f125_udp.telemetry_mapper import map_telemetry_point


def test_map_telemetry_point_clamps_brake_and_throttle_to_valid_range():
    header = PacketHeader()
    header.m_sessionTime = 12.5

    car = CarTelemetryData()
    car.m_speed = 180
    car.m_throttle = 1.7
    car.m_steer = -0.25
    car.m_brake = 3.4
    car.m_gear = 3
    car.m_engineRPM = 9000
    car.m_drs = 1

    point = map_telemetry_point(header, car, 0.42)

    assert point.throttle == 1.0
    assert point.brake == 1.0
    assert point.speed == 180.0
    assert point.rpm == 9000
    assert point.track_position == 0.42
