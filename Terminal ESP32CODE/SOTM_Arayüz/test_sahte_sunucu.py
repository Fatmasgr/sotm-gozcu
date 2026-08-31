from __future__ import annotations

import pytest

from sahte_sunucu import SimulatedController


@pytest.mark.parametrize(
    "komut",
    [
        {"komut": "ping"},
        {"komut": "git", "azimut": 170.0, "elevasyon": 45.0},
        {"komut": "mod_degistir", "mod": "otomatik"},
        {"komut": "duzelt", "delta_azimuth": 0.1, "delta_elevation": -0.1},
        {"komut": "pid_oku"},
        {
            "komut": "pid_uygula",
            "azimut": {"p": 2.0, "i": 0.2, "d": 0.5},
            "elevasyon": {"p": 2.5, "i": 0.3, "d": 0.6},
        },
        {"komut": "sifirla"},
        {"komut": "hata_temizle"},
        {"komut": "dur"},
    ],
)
def test_tum_protokol_komutlari_ack_uretir(komut: dict) -> None:
    yanitlar = SimulatedController().command(komut)
    ackler = [yanit for yanit in yanitlar if yanit.get("type") == "ack"]
    assert ackler, f"ACK üretilmedi: {komut['komut']}"
    assert ackler[-1]["cmd"] == komut["komut"]
    assert ackler[-1]["ok"] is True


def test_sanal_kontrolcu_hedefe_yaklasir() -> None:
    kontrolcu = SimulatedController()
    kontrolcu.command({"komut": "git", "azimut": 170.0, "elevasyon": 45.0})
    ilk_hata = kontrolcu.telemetry()["hata_acisi"]
    for _ in range(30):
        son = kontrolcu.telemetry()
    assert son["hata_acisi"] < ilk_hata
    assert son["hedefe_ulasildi"]
