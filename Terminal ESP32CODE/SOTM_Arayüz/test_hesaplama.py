from __future__ import annotations

import math

import pytest

import config
from hesaplama import hesapla_azimut_elevasyon, piksel_hatasini_aciya_cevir


def test_konya_turksat_4b_bakis_acisi_makul() -> None:
    azimut, elevasyon = hesapla_azimut_elevasyon(
        37.8746, 32.4932, 42.0, 1020.0
    )
    assert 164.0 < azimut < 168.0
    assert 42.0 < elevasyon < 45.0


def test_ekvator_ve_ayni_boylamda_uydu_zenite_yakindir() -> None:
    azimut, elevasyon = hesapla_azimut_elevasyon(0.0, 42.0, 42.0, 0.0)
    assert math.isfinite(azimut)
    assert elevasyon == pytest.approx(90.0, abs=0.01)


@pytest.mark.parametrize(
    ("enlem", "boylam"),
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0)],
)
def test_gecersiz_koordinatlar_reddedilir(enlem: float, boylam: float) -> None:
    with pytest.raises(ValueError):
        hesapla_azimut_elevasyon(enlem, boylam, 42.0)


def test_piksel_hatasi_gorus_acisina_gore_cevrilir() -> None:
    azimut, elevasyon = piksel_hatasini_aciya_cevir(
        config.FRAME_WIDTH / 2,
        config.FRAME_HEIGHT / 2,
    )
    assert azimut == -config.MAX_CAMERA_CORRECTION_DEG
    assert elevasyon == config.MAX_CAMERA_CORRECTION_DEG

