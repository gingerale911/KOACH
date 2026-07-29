"""Assetto Corsa Remote Telemetry UDP struct tanımları (ctypes).

Referans: AC Remote Telemetry Documentation.

KRİTİK FARK — F1 25'ten: burada _pack_ = 1 KULLANILMIYOR. F1 25 spec'i
açıkça 1-byte hizalama (packed struct) kullanıyordu; AC belgesinde böyle
bir belirtme yok — yani derleyicinin DOĞAL hizalamasını (natural
alignment) kullandığı varsayılıyor. ctypes.Structure, _pack_ atanmadığında
bunu zaten otomatik uygular (her alan kendi boyutuna göre hizalanır,
aradaki boşluklar tipik bir C derleyicisi gibi otomatik eklenir).

Bu varsayım gerçek bir AC sunucusuna bağlanılıp test edilmeden %100
doğrulanmış sayılmaz — RTCarInfo/RTLap'in beklenen boyutları
(RTCARINFO_SIZE, RTLAP_SIZE) log'a yazdırılıp gelen paket boyutlarıyla
karşılaştırılarak ilk bağlantıda teyit edilmeli.
"""

import ctypes

UDP_PORT_DEFAULT = 9996

# handshaker.operationId değerleri
OP_HANDSHAKE = 0
OP_SUBSCRIBE_UPDATE = 1
OP_SUBSCRIBE_SPOT = 2
OP_DISMISS = 3


class Handshaker(ctypes.Structure):
    """Client → Server: handshake / abonelik / çıkış paketi."""
    _fields_ = [
        ("identifier", ctypes.c_int32),
        ("version", ctypes.c_int32),
        ("operationId", ctypes.c_int32),
    ]


class HandshakerResponse(ctypes.Structure):
    """Server → Client: handshake cevabı."""
    _fields_ = [
        ("carName", ctypes.c_char * 50),
        ("driverName", ctypes.c_char * 50),
        ("identifier", ctypes.c_int32),
        ("version", ctypes.c_int32),
        ("trackName", ctypes.c_char * 50),
        ("trackConfig", ctypes.c_char * 50),
    ]


class RTCarInfo(ctypes.Structure):
    """Server → Client: her fizik adımında gelen tam telemetri karesi
    (SUBSCRIBE_UPDATE aboneliğiyle). Hiçbir alan atlanmadı — proje kararı:
    ham veri filtrelenmeden tutulacak."""
    _fields_ = [
        ("identifier", ctypes.c_char),
        ("size", ctypes.c_int32),
        ("speed_Kmh", ctypes.c_float),
        ("speed_Mph", ctypes.c_float),
        ("speed_Ms", ctypes.c_float),
        ("isAbsEnabled", ctypes.c_bool),
        ("isAbsInAction", ctypes.c_bool),
        ("isTcInAction", ctypes.c_bool),
        ("isTcEnabled", ctypes.c_bool),
        ("isInPit", ctypes.c_bool),
        ("isEngineLimiterOn", ctypes.c_bool),
        ("accG_vertical", ctypes.c_float),
        ("accG_horizontal", ctypes.c_float),
        ("accG_frontal", ctypes.c_float),
        ("lapTime", ctypes.c_int32),
        ("lastLap", ctypes.c_int32),
        ("bestLap", ctypes.c_int32),
        ("lapCount", ctypes.c_int32),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("clutch", ctypes.c_float),
        ("engineRPM", ctypes.c_float),
        ("steer", ctypes.c_float),
        ("gear", ctypes.c_int32),
        ("cgHeight", ctypes.c_float),
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("slipAngle", ctypes.c_float * 4),
        ("slipAngle_ContactPatch", ctypes.c_float * 4),
        ("slipRatio", ctypes.c_float * 4),
        ("tyreSlip", ctypes.c_float * 4),
        ("ndSlip", ctypes.c_float * 4),
        ("load", ctypes.c_float * 4),
        ("Dy", ctypes.c_float * 4),
        ("Mz", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("camberRAD", ctypes.c_float * 4),
        ("tyreRadius", ctypes.c_float * 4),
        ("tyreLoadedRadius", ctypes.c_float * 4),
        ("suspensionHeight", ctypes.c_float * 4),
        ("carPositionNormalized", ctypes.c_float),
        ("carSlope", ctypes.c_float),
        ("carCoordinates", ctypes.c_float * 3),
    ]


class RTLap(ctypes.Structure):
    """Server → Client: bir tur bittiğinde gelen olay paketi
    (SUBSCRIBE_SPOT aboneliğiyle). Session'daki TÜM araçlar için gelir —
    bize ait olup olmadığı driverName karşılaştırmasıyla tespit edilir
    (bkz. proje kararı: carIdentifierNumber güvenilir referans değil)."""
    _fields_ = [
        ("carIdentifierNumber", ctypes.c_int32),
        ("lap", ctypes.c_int32),
        ("driverName", ctypes.c_char * 50),
        ("carName", ctypes.c_char * 50),
        ("time", ctypes.c_int32),
    ]


HANDSHAKE_RESPONSE_SIZE = ctypes.sizeof(HandshakerResponse)
RTCARINFO_SIZE = ctypes.sizeof(RTCarInfo)
RTLAP_SIZE = ctypes.sizeof(RTLap)