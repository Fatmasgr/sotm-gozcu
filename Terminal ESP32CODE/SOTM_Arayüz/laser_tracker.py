"""
Lazer kayıp olduğunda (görüntüden birkaç kare boyunca kaybolduğunda)
konumunu tahmin etmek ve tespit gürültüsünü yumuşatmak için Kalman filtresi.

Bu modül tespiti YAPMAZ (onu laser_detector.py yapar); sadece gelen
ham (x, y) ölçümünü yumuşatır ve ölçüm yokken kısa süreliğine tahmin üretir.
"""

from typing import Optional, Tuple

import cv2
import numpy as np

import config


def _clamp_point(x: float, y: float, frame_width: int, frame_height: int) -> Tuple[int, int]:
    max_x, max_y = frame_width - 1, frame_height - 1
    return int(np.clip(x, 0, max_x)), int(np.clip(y, 0, max_y))


class LaserTracker:
    """Sabit hızlı hareket modeli ile 2D Kalman filtresi (x, y, vx, vy)."""

    def __init__(
        self,
        process_noise: float = config.KALMAN_PROCESS_NOISE,
        measurement_noise: float = config.KALMAN_MEASUREMENT_NOISE,
    ):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]], np.float32
        )
        self.kf.transitionMatrix = np.array(
            [[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32
        )
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * process_noise
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * measurement_noise
        self.initialized = False

    def update(
        self, x: float, y: float, frame_width: int, frame_height: int
    ) -> Tuple[int, int]:
        """Yeni bir ham ölçüm geldiğinde çağrılır; yumuşatılmış konumu döner."""
        measurement = np.array([[np.float32(x)], [np.float32(y)]])

        if not self.initialized:
            self.kf.statePre = np.array([[x], [y], [0], [0]], np.float32)
            self.kf.statePost = np.array([[x], [y], [0], [0]], np.float32)
            self.initialized = True

        self.kf.correct(measurement)
        prediction = self.kf.predict()
        return _clamp_point(prediction[0][0], prediction[1][0], frame_width, frame_height)

    def predict(
        self, frame_width: int, frame_height: int
    ) -> Optional[Tuple[int, int]]:
        """Ölçüm yokken (lazer görünmüyorken) son duruma göre tahmin üretir."""
        if not self.initialized:
            return None
        prediction = self.kf.predict()
        return _clamp_point(prediction[0][0], prediction[1][0], frame_width, frame_height)

    def reset(self) -> None:
        """Filtreyi sıfırlar (lazer uzun süre kaybolduğunda çağrılır)."""
        self.initialized = False
