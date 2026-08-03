"""
Hedef merkezi tespiti, piksel hata hesabı, kalibrasyon (px -> cm),
skor hesaplama ve hedef kilitleme mantığı.

NOT: Hedef merkezi şu an görüntünün tam merkezi olarak kabul edilir.
İleride gerçek bir hedef tespiti (ör. daire/nesne tanıma) eklenirse
sadece get_target_center() fonksiyonu değiştirilecek; geri kalan
tüm hesaplamalar (error_x, error_y, mesafe, skor) aynı kalır.
"""

import math
from typing import Optional, Tuple

import config
from data_model import TargetingData


def get_target_center(frame_width: int, frame_height: int) -> Tuple[int, int]:
    """Mevcut hedef merkezi yaklaşımı: görüntünün tam merkezi."""
    return frame_width // 2, frame_height // 2


def calculate_pixel_error(
    laser_x: int, laser_y: int, target_x: int, target_y: int
) -> Tuple[int, int]:
    """
    error_x = laser_x - target_x
    error_y = laser_y - target_y
    Bu değerler pan-tilt yön kararı için ileride doğrudan kullanılacaktır.
    """
    error_x = laser_x - target_x
    error_y = laser_y - target_y
    return error_x, error_y


def calculate_pixel_distance(error_x: int, error_y: int) -> float:
    """Lazer ile hedef merkezi arasındaki Öklid mesafesi (piksel)."""
    return math.sqrt(error_x ** 2 + error_y ** 2)


def pixel_to_cm(
    pixel_distance: float,
    max_radius_pixels: float = config.MAX_RADIUS_PIXELS,
    outer_radius_cm: float = config.OUTER_RADIUS_CM,
) -> float:
    """Mevcut kalibrasyon mantığı: doğrusal piksel -> cm dönüşümü."""
    return (pixel_distance / max_radius_pixels) * outer_radius_cm


def calculate_score(cm_distance: float) -> int:
    """Mevcut skor eşikleri ile birebir aynı mantık."""
    for upper_bound_cm, score in config.SCORE_THRESHOLDS:
        if cm_distance <= upper_bound_cm:
            return score
    return config.DEFAULT_SCORE


def is_target_locked(
    cm_distance: float,
    threshold_cm: float = config.TARGET_LOCK_THRESHOLD_CM,
) -> bool:
    """Lazer, hedefe yeterince yaklaştıysa (eşik altında) True döner."""
    return cm_distance <= threshold_cm


def build_targeting_data(
    laser_detected: bool,
    laser_predicted: bool,
    laser_x: Optional[int],
    laser_y: Optional[int],
    frame_width: int,
    frame_height: int,
) -> TargetingData:
    """
    Çözümlenmiş lazer konumunu (gerçek ölçüm ya da Kalman tahmini) alır,
    hedef merkeziyle karşılaştırır ve arayüz entegrasyonuna hazır tam veri
    paketini üretir.

    - laser_detected: bu karede lazer gerçekten (ham olarak) görüldü mü
    - laser_predicted: laser_x/laser_y gerçek ölçüm değil, tahmin mi
    - laser_x/laser_y: None ise lazer tamamen kayıp demektir
      (ne ölçüm ne tahmin mevcut)
    """
    target_x, target_y = get_target_center(frame_width, frame_height)

    if laser_x is None or laser_y is None:
        return TargetingData.no_laser(target_x, target_y)

    error_x, error_y = calculate_pixel_error(laser_x, laser_y, target_x, target_y)
    pixel_distance = calculate_pixel_distance(error_x, error_y)
    cm_distance = pixel_to_cm(pixel_distance)
    score = calculate_score(cm_distance)
    locked = is_target_locked(cm_distance) and laser_detected

    return TargetingData(
        laser_detected=laser_detected,
        laser_x=laser_x,
        laser_y=laser_y,
        target_x=target_x,
        target_y=target_y,
        error_x=error_x,
        error_y=error_y,
        pixel_distance=pixel_distance,
        cm_distance=cm_distance,
        score=score,
        target_locked=locked,
        laser_predicted=laser_predicted,
    )
