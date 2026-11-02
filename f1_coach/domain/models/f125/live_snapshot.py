"""Live snapshot of vehicle, race, and driver telemetry for real-time dashboards."""

from dataclasses import dataclass, field
import math
import time


@dataclass
class LiveTelemetrySnapshot:
    """Thread-safe snapshot updated by incoming UDP packets."""

    # Session & Track
    track_id: int = -1
    track_name: str = "HOCKENHEIM"
    session_type_name: str = "PRACTICE"
    total_laps: int = 67
    track_length: float = 4574.0

    # Weather & Atmosphere
    air_temperature: int = 24
    track_temperature: int = 34
    weather_name: str = "Clear"
    rain_percentage: int = 0
    humidity: int = 58
    air_pressure_mb: int = 1013
    wind_speed_kmh: float = 8.5

    # Race & Timing
    car_position: int = 1
    current_lap_num: int = 1
    current_lap_time_ms: int = 0
    last_lap_time_ms: int = 0
    best_lap_time_ms: int = 0
    lap_distance: float = 0.0
    delta_to_front_ms: int = 0

    # Powertrain & Motion
    speed_kmh: int = 0
    max_speed_kmh: int = 0
    gear: int = 0
    engine_rpm: int = 0
    max_rpm: int = 13500
    throttle: float = 0.0
    steer: float = 0.0
    brake: float = 0.0
    drs_active: bool = False
    engine_temperature: int = 95

    # 4-Wheel Temperatures & Pressures (Order in F1 UDP: 0=RL, 1=RR, 2=FL, 3=FR)
    tyres_surface_temp: tuple[int, int, int, int] = (104, 105, 104, 105)
    tyres_inner_temp: tuple[int, int, int, int] = (100, 100, 100, 100)
    tyres_pressure_psi: tuple[float, float, float, float] = (22.5, 22.5, 24.0, 24.0)
    brakes_temperature: tuple[int, int, int, int] = (520, 510, 650, 620)

    # Car damage (packet 10); damage_received is False until the first packet arrives
    damage_received: bool = False
    tyres_wear_pct: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    tyres_damage_pct: tuple[int, int, int, int] = (0, 0, 0, 0)
    front_left_wing_damage: int = 0
    front_right_wing_damage: int = 0
    rear_wing_damage: int = 0
    floor_damage: int = 0
    diffuser_damage: int = 0
    sidepod_damage: int = 0
    gearbox_damage: int = 0
    engine_damage: int = 0

    # Energy & Fuel
    fuel_in_tank: float = 52.4
    fuel_capacity: float = 110.0
    fuel_remaining_laps: float = 28.5
    ers_store_energy: float = 4000000.0  # Max 4MJ in F1

    # Dynamic G-Forces
    g_force_lateral: float = 0.0
    g_force_longitudinal: float = 0.0
    g_force_vertical: float = 0.0
    world_x: float = 0.0
    world_z: float = 0.0

    last_packet_timestamp: float = field(default_factory=time.monotonic)

    # --- Convenience Corner Accessors ---
    @property
    def fl_tyre_temp(self) -> int:
        return self.tyres_surface_temp[2]

    @property
    def fr_tyre_temp(self) -> int:
        return self.tyres_surface_temp[3]

    @property
    def rl_tyre_temp(self) -> int:
        return self.tyres_surface_temp[0]

    @property
    def rr_tyre_temp(self) -> int:
        return self.tyres_surface_temp[1]

    @property
    def fl_tyre_pressure_bar(self) -> float:
        # 1 PSI ≈ 0.0689476 bar
        return round(self.tyres_pressure_psi[2] * 0.06895, 1)

    @property
    def fr_tyre_pressure_bar(self) -> float:
        return round(self.tyres_pressure_psi[3] * 0.06895, 1)

    @property
    def rl_tyre_pressure_bar(self) -> float:
        return round(self.tyres_pressure_psi[0] * 0.06895, 1)

    @property
    def rr_tyre_pressure_bar(self) -> float:
        return round(self.tyres_pressure_psi[1] * 0.06895, 1)

    @property
    def fl_brake_temp(self) -> int:
        return self.brakes_temperature[2]

    @property
    def fr_brake_temp(self) -> int:
        return self.brakes_temperature[3]

    @property
    def rl_brake_temp(self) -> int:
        return self.brakes_temperature[0]

    @property
    def rr_brake_temp(self) -> int:
        return self.brakes_temperature[1]

    @property
    def fuel_percent(self) -> float:
        if self.fuel_capacity <= 0:
            return 50.0
        return min(100.0, max(0.0, (self.fuel_in_tank / self.fuel_capacity) * 100.0))

    @property
    def ers_percent(self) -> float:
        return min(100.0, max(0.0, (self.ers_store_energy / 4000000.0) * 100.0))

    @property
    def lap_progress(self) -> float:
        if self.track_length <= 0:
            return 0.0
        return max(0.0, min(1.0, self.lap_distance / self.track_length))

    # --- Biometric Real-Time Estimations ---
    def calculate_driver_stress(self) -> float:
        """Physical stress index (0 to 100) based on instant 3-axis G forces and control intensity."""
        g_mag = math.sqrt(self.g_force_lateral**2 + self.g_force_longitudinal**2)
        pedal_load = (self.throttle + self.brake * 1.5) * 20.0
        speed_factor = min(30.0, (self.speed_kmh / 330.0) * 30.0)
        stress = min(100.0, max(12.0, (g_mag * 16.0) + pedal_load + speed_factor))
        return stress

    def calculate_heart_rate(self, current_time: float) -> int:
        """Dynamic cardiac pulse (BPM) fluctuating naturally with race exertion."""
        base_bpm = 72.0
        stress = self.calculate_driver_stress()
        target_bpm = base_bpm + (stress * 0.95)  # Scale between 72 and ~165 BPM
        micro_variation = math.sin(current_time * 2.5) * 3.0
        return int(max(60, min(185, target_bpm + micro_variation)))

    def calculate_respiration_rate(self) -> int:
        """Breaths per minute based on physical work rate."""
        stress = self.calculate_driver_stress()
        return int(max(10, min(30, 12 + (stress * 0.16))))
