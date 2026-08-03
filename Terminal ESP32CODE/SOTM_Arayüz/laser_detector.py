"""
Kırmızı lazer noktasının HSV renk filtreleme ile tespiti.
Mevcut kodun tespit mantığı (maske + kontur + minEnclosingCircle)
birebir korunmuştur; sadece fonksiyon haline getirilmiştir.
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

import config


@dataclass
class LaserDetectionResult:
    detected: bool
    x: Optional[int] = None
    y: Optional[int] = None
    area: float = 0.0


class LaserDetector:
    def __init__(
        self,
        lower_red_1=config.LOWER_RED_1,
        upper_red_1=config.UPPER_RED_1,
        lower_red_2=config.LOWER_RED_2,
        upper_red_2=config.UPPER_RED_2,
        min_area=config.MIN_CONTOUR_AREA,
    ):
        self.lower_red_1 = np.array(lower_red_1)
        self.upper_red_1 = np.array(upper_red_1)
        self.lower_red_2 = np.array(lower_red_2)
        self.upper_red_2 = np.array(upper_red_2)
        self.min_area = min_area

    def _build_mask(self, hsv_frame: np.ndarray) -> np.ndarray:
        mask1 = cv2.inRange(hsv_frame, self.lower_red_1, self.upper_red_1)
        mask2 = cv2.inRange(hsv_frame, self.lower_red_2, self.upper_red_2)
        mask = cv2.bitwise_or(mask1, mask2)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        return mask

    def detect(self, frame: np.ndarray) -> LaserDetectionResult:
        """
        Verilen BGR frame içinde en büyük kırmızı konturu bulur ve
        onu lazer noktası olarak kabul eder (mevcut mantık ile aynı).
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self._build_mask(hsv)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return LaserDetectionResult(detected=False)

        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)

        if area <= self.min_area:
            return LaserDetectionResult(detected=False)

        (x, y), _radius = cv2.minEnclosingCircle(largest_contour)
        return LaserDetectionResult(detected=True, x=int(x), y=int(y), area=area)
