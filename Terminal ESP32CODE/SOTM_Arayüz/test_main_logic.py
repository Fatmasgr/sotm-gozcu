from __future__ import annotations

from main import AnaPencere


class _SahtePencere:
    def __init__(self, mod: str = "otomatik") -> None:
        self.su_anki_mod = mod
        self.manuel_cagrilari: list[bool] = []
        self.loglar: list[tuple] = []

    def manuel_mod_tiklandi(self, _checked=False, gonder: bool = True) -> None:
        self.su_anki_mod = "manuel"
        self.manuel_cagrilari.append(gonder)

    def log_yaz(self, *args) -> None:
        self.loglar.append(args)


def test_reddedilen_otomatik_mod_arayuzu_manuele_dondurur() -> None:
    pencere = _SahtePencere()
    AnaPencere._ack_mesajini_isle(
        pencere,
        {
            "type": "ack",
            "cmd": "mod_degistir",
            "ok": False,
            "message": "Kalibrasyon eksik.",
        },
    )
    assert pencere.su_anki_mod == "manuel"
    assert pencere.manuel_cagrilari == [False]


def test_durdur_onayi_arayuzu_manuele_dondurur() -> None:
    pencere = _SahtePencere()
    AnaPencere._ack_mesajini_isle(
        pencere,
        {
            "type": "ack",
            "cmd": "dur",
            "ok": True,
            "message": "Motorlar durduruldu.",
        },
    )
    assert pencere.su_anki_mod == "manuel"
    assert pencere.manuel_cagrilari == [False]
