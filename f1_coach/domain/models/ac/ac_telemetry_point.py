"""AcTelemetryPoint domain model.

Assetto Corsa'nın RTCarInfo UDP struct'ından türetilen, "wide" formatlı
(F1 25'in TelemetryPoint'i gibi) bir telemetri karesi. FSAE'nin CAN
verisinden farklı olarak burada kanal seti sabit ve önceden bilinen bir
struct — bu yüzden kullanıcı etiketlemesine gerek yok, F1 25 modülündeki
gibi doğrudan alan bazlı bir domain modeli yeterli.

Hiçbir alan filtrelenmedi — RTCarInfo'daki her sinyal burada karşılığını
buluyor (proje kararı: seçici olmak yerine ham veriyi eksiksiz saklamak).

Tekerlek bazlı alanlar (4 elemanlı tuple'lar) AC'nin standart sırasını
izlediği varsayılıyor: (ön-sol, ön-sağ, arka-sol, arka-sağ). Bu belgede
teyit edilmemiş bir varsayım — gerçek veriyle doğrulanmalı.
"""

from dataclasses import dataclass

WheelQuad = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class AcTelemetryPoint:
    """Bir fizik adımında (RTCarInfo paketinde) yakalanan tüm telemetri.

    Attributes:
        timestamp:                  Session başlangıcından itibaren geçen
                                    saniye — paket bizim tarafımızda
                                    alındığı anda üretilir (struct'ın
                                    kendisinde zaman damgası yok).
        speed_kmh / speed_mph / speed_ms: Hız, üç birimde de.
        is_abs_enabled / is_abs_in_action: ABS açık mı / şu an müdahale
                                    ediyor mu.
        is_tc_enabled / is_tc_in_action:  Traksiyon kontrolü açık mı / şu
                                    an müdahale ediyor mu.
        is_in_pit:                  Araç pitte mi.
        is_engine_limiter_on:       Motor rev limiter devrede mi.
        acc_g_vertical / acc_g_horizontal / acc_g_frontal: G-force, üç eksende.
        lap_time_ms / last_lap_ms / best_lap_ms: Anlık/son/en iyi tur
                                    süresi (milisaniye, oyunun kendi
                                    sayacı — RTLap'teki nihai süreyle
                                    karşılaştırılabilir).
        lap_count:                  Tamamlanan tur sayısı.
        throttle / brake / clutch:  0.0–1.0 aralığında pedal uygulaması.
        engine_rpm:                 Motor devri.
        steer:                      Direksiyon girdisi (ham, AC birimi).
        gear:                       Seçili vites.
        cg_height:                  Ağırlık merkezi yüksekliği.
        wheel_angular_speed:        Tekerlek açısal hızı, 4 tekerlek.
        slip_angle:                 Kayma açısı, 4 tekerlek.
        slip_angle_contact_patch:   Kontak yamasında kayma açısı, 4 tekerlek.
        slip_ratio:                 Kayma oranı, 4 tekerlek.
        tyre_slip:                  Lastik kayması, 4 tekerlek.
        nd_slip:                    Normalize edilmiş kayma, 4 tekerlek.
        load:                       Lastik yükü, 4 tekerlek.
        dy:                         Yanal kuvvet katsayısı, 4 tekerlek.
        mz:                         Self-aligning moment, 4 tekerlek.
        tyre_dirty_level:           Lastik kirlilik seviyesi, 4 tekerlek.
        camber_rad:                 Kamber açısı (radyan), 4 tekerlek.
        tyre_radius:                Lastik yarıçapı, 4 tekerlek.
        tyre_loaded_radius:         Yük altında lastik yarıçapı, 4 tekerlek.
        suspension_height:          Süspansiyon yüksekliği, 4 tekerlek.
        car_position_normalized:    Pist üzerindeki normalize konum
                                    (0.0–1.0) — grafiklerde x-ekseni
                                    olarak kullanılır, F125'teki
                                    track_position'ın karşılığı.
        car_slope:                  Aracın bulunduğu pist eğimi.
        car_coordinates:            Dünya koordinatları (x, y, z).
    """

    timestamp: float

    speed_kmh: float
    speed_mph: float
    speed_ms: float

    is_abs_enabled: bool
    is_abs_in_action: bool
    is_tc_enabled: bool
    is_tc_in_action: bool
    is_in_pit: bool
    is_engine_limiter_on: bool

    acc_g_vertical: float
    acc_g_horizontal: float
    acc_g_frontal: float

    lap_time_ms: int
    last_lap_ms: int
    best_lap_ms: int
    lap_count: int

    throttle: float
    brake: float
    clutch: float
    engine_rpm: float
    steer: float
    gear: int
    cg_height: float

    wheel_angular_speed: WheelQuad
    slip_angle: WheelQuad
    slip_angle_contact_patch: WheelQuad
    slip_ratio: WheelQuad
    tyre_slip: WheelQuad
    nd_slip: WheelQuad
    load: WheelQuad
    dy: WheelQuad
    mz: WheelQuad
    tyre_dirty_level: WheelQuad
    camber_rad: WheelQuad
    tyre_radius: WheelQuad
    tyre_loaded_radius: WheelQuad
    suspension_height: WheelQuad

    car_position_normalized: float
    car_slope: float
    car_coordinates: tuple[float, float, float]