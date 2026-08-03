from __future__ import annotations

import cv2
import numpy as np
import pytest

import config
from laser_detector import LaserDetector
from laser_pipeline import LaserTargetSystem
from targeting import build_targeting_data, calculate_score, pixel_to_cm


def test_hedef_merkezinde_kilit() -> None:
    data = build_targeting_data(True, False, 400, 300, 800, 600)
    assert data.target_locked
    assert data.error_x == 0
    assert data.error_y == 0
    assert data.cm_distance == 0
    assert data.score == 10


def test_tahmini_nokta_kilit_sayilmaz() -> None:
    data = build_targeting_data(False, True, 400, 300, 800, 600)
    assert data.laser_predicted
    assert not data.target_locked


def test_piksel_santimetre_kalibrasyonu() -> None:
    assert pixel_to_cm(250) == pytest.approx(50.0)
    assert calculate_score(5.0) == 10
    assert calculate_score(25.0) == 6
    assert calculate_score(25.1) == 5


def test_opencv_kirmizi_lazer_noktasini_bulur() -> None:
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.circle(frame, (430, 280), 7, (0, 0, 255), thickness=-1)

    sonuc = LaserDetector().detect(frame)

    assert sonuc.detected
    assert sonuc.x == pytest.approx(430, abs=2)
    assert sonuc.y == pytest.approx(280, abs=2)
    assert sonuc.area > config.MIN_CONTOUR_AREA


def test_tam_lazer_islem_hatti_kilit_tahmin_ve_kayip() -> None:
    sistem = LaserTargetSystem()
    merkez_lazer = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.circle(merkez_lazer, (400, 300), 7, (0, 0, 255), thickness=-1)

    islenmis, ilk = sistem.process_frame(merkez_lazer)
    assert islenmis.shape == merkez_lazer.shape
    assert ilk.laser_detected
    assert ilk.target_locked

    bos = np.zeros_like(merkez_lazer)
    _, tahmin = sistem.process_frame(bos.copy())
    assert not tahmin.laser_detected
    assert tahmin.laser_predicted
    assert tahmin.laser_x is not None

    son = tahmin
    for _ in range(config.PREDICT_AFTER_LOST_FRAMES):
        _, son = sistem.process_frame(bos.copy())
    assert not son.laser_detected
    assert not son.laser_predicted
    assert son.laser_x is None
    assert son.laser_y is None
