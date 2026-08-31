"""Uydu bakış açısı ve kamera hata açısı hesapları."""

from __future__ import annotations

import math

import config

EARTH_EQUATORIAL_RADIUS_KM = 6378.137
GEOSTATIONARY_RADIUS_KM = 42164.0


def _sonlu_sayi(deger: float, ad: str) -> float:
    deger = float(deger)
    if not math.isfinite(deger):
        raise ValueError(f"{ad} sonlu bir sayı olmalıdır.")
    return deger


def hesapla_azimut_elevasyon(
    enlem: float,
    boylam: float,
    uydu_boylami: float,
    yukseklik_m: float = 0.0,
) -> tuple[float, float]:
    """Jeostasyoner uydu için gerçek kuzeye göre azimut/elevasyon döndürür."""
    enlem = _sonlu_sayi(enlem, "Enlem")
    boylam = _sonlu_sayi(boylam, "Boylam")
    uydu_boylami = _sonlu_sayi(uydu_boylami, "Uydu boylamı")
    yukseklik_m = _sonlu_sayi(yukseklik_m, "Yükseklik")

    if not -90.0 <= enlem <= 90.0:
        raise ValueError("Enlem -90 ile +90 derece arasında olmalıdır.")
    if not -180.0 <= boylam <= 180.0:
        raise ValueError("Boylam -180 ile +180 derece arasında olmalıdır.")
    if not -180.0 <= uydu_boylami <= 180.0:
        raise ValueError("Uydu boylamı -180 ile +180 derece arasında olmalıdır.")
    if yukseklik_m < -500.0 or yukseklik_m > 10_000.0:
        raise ValueError("Yükseklik -500 ile 10000 metre arasında olmalıdır.")

    enlem_rad = math.radians(enlem)
    delta_lambda_rad = math.radians(uydu_boylami - boylam)
    cos_merkez_aci = math.cos(enlem_rad) * math.cos(delta_lambda_rad)
    cos_merkez_aci = max(-1.0, min(1.0, cos_merkez_aci))

    azimut_rad = math.atan2(
        math.sin(delta_lambda_rad),
        -math.sin(enlem_rad) * math.cos(delta_lambda_rad),
    )
    azimut_derece = math.degrees(azimut_rad) % 360.0

    istasyon_yaricapi_km = EARTH_EQUATORIAL_RADIUS_KM + yukseklik_m / 1000.0
    yaricap_orani = istasyon_yaricapi_km / GEOSTATIONARY_RADIUS_KM
    yatay_bilesen = math.sqrt(max(0.0, 1.0 - cos_merkez_aci**2))
    elevasyon_rad = math.atan2(cos_merkez_aci - yaricap_orani, yatay_bilesen)
    elevasyon_derece = math.degrees(elevasyon_rad)

    return round(azimut_derece, 2), round(elevasyon_derece, 2)


def piksel_hatasini_aciya_cevir(
    error_x: float,
    error_y: float,
    frame_width: int = config.FRAME_WIDTH,
    frame_height: int = config.FRAME_HEIGHT,
) -> tuple[float, float]:
    """Piksel hatasını kamera görüş açısına göre sınırlı düzeltmeye çevirir."""
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Kare boyutları sıfırdan büyük olmalıdır.")

    duzeltme_azimut = (
        -float(error_x) * config.CAMERA_HORIZONTAL_FOV_DEG / float(frame_width)
    )
    duzeltme_elevasyon = (
        float(error_y) * config.CAMERA_VERTICAL_FOV_DEG / float(frame_height)
    )
    sinir = config.MAX_CAMERA_CORRECTION_DEG
    return (
        max(-sinir, min(sinir, duzeltme_azimut)),
        max(-sinir, min(sinir, duzeltme_elevasyon)),
    )
