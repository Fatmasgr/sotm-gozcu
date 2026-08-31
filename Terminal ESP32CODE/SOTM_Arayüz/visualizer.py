"""
Görüntü üzerine görsel bilgilerin (hedef merkezi, lazer noktası,
aralarındaki fark çizgisi, koordinatlar, mesafe, skor, kilit durumu)
çizilmesinden sorumlu modül.
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from data_model import TargetingData

Point = Optional[Tuple[int, int]]

# Renkler (BGR)
COLOR_TARGET = (255, 0, 0)      # mavi
COLOR_LASER = (0, 255, 0)       # yeşil
COLOR_ERROR_LINE = (0, 165, 255)  # turuncu
COLOR_TEXT = (0, 0, 0)    # beyaz(255,255,255) siyah
COLOR_SCORE = (0, 255, 255)     # sarı
COLOR_LOCKED = (0, 255, 0)      # yeşil
COLOR_NOT_LOCKED = (0, 0, 255)  # kırmızı
COLOR_PREDICTED = (0, 190, 255)  # amber (tahmini konum)
COLOR_TRAIL = (0, 255, 90)       # iz rengi


def draw_targeting_overlay(frame: np.ndarray, data: TargetingData) -> np.ndarray:
    """Verilen TargetingData'ya göre frame üzerine tüm görselleri çizer."""

    # Hedef merkezini göster
    cv2.circle(frame, (data.target_x, data.target_y), 5, COLOR_TARGET, -1)

    # laser_x/laser_y None ise ne gerçek ölçüm ne de tahmin var demektir
    if data.laser_x is None or data.laser_y is None:
        cv2.putText(
            frame, "Lazer bulunamadi", (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_NOT_LOCKED, 2
        )
        return frame

    # Lazer noktasını göster (tahmin ise farklı renkle, kesikli çember)
    laser_color = COLOR_PREDICTED if data.laser_predicted else COLOR_LASER
    cv2.circle(frame, (data.laser_x, data.laser_y), 10, laser_color, 2)

    # Lazer ile hedef merkezi arasındaki farkı görsel olarak göster
    cv2.line(
        frame,
        (data.target_x, data.target_y),
        (data.laser_x, data.laser_y),
        COLOR_ERROR_LINE,
        2,
    )

    # Lazer koordinatlarını göster (tahminse belirt)
    coord_label = f"X: {data.laser_x}  Y: {data.laser_y}"
    if data.laser_predicted:
        coord_label += " (tahmin)"
    cv2.putText(
        frame, coord_label, (data.laser_x + 10, data.laser_y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2,
    )

    # Skoru göster
    cv2.putText(
        frame, f"Score: {data.score}", (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_SCORE, 3,
    )

    # Piksel mesafesini göster
    cv2.putText(
        frame, f"Pixel Dist: {data.pixel_distance:.2f} px", (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_TEXT, 2,
    )

    # Santimetre cinsinden mesafeyi göster
    cv2.putText(
        frame, f"Distance: {data.cm_distance:.2f} cm", (20, 115),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_TEXT, 2,
    )

    # Hata değerlerini göster (error_x / error_y)
    cv2.putText(
        frame, f"Error X: {data.error_x} px  Error Y: {data.error_y} px",
        (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2,
    )

    # Hedef kilitlenme durumunu göster
    lock_color = COLOR_LOCKED if data.target_locked else COLOR_NOT_LOCKED
    lock_text = "TARGET LOCKED" if data.target_locked else "NOT LOCKED"
    cv2.putText(
        frame, lock_text, (20, 190),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, lock_color, 2,
    )

    return frame


def draw_trail(frame: np.ndarray, trail_points: List[Point]) -> np.ndarray:
    """
    Lazerin son N konumunu, ana görüntü üzerine soluklaşan (fade)
    bir çizgi olarak çizer. `None` olan noktalar kopukluk demektir
    (lazer o an kaybolmuştu) ve çizgiyi böler.
    """
    for i in range(1, len(trail_points)):
        prev_point, point = trail_points[i - 1], trail_points[i]
        if prev_point is None or point is None:
            continue

        alpha = i / max(1, len(trail_points) - 1)
        # Eskiden yeniye doğru soluk -> canlı renk geçişi
        color = (0, int(120 + 135 * alpha), int(255 * alpha))
        thickness = max(1, int(4 * alpha))
        cv2.line(frame, prev_point, point, color, thickness, cv2.LINE_AA)

    return frame
