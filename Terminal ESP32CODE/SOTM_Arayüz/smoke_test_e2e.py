"""Sahte ESP32-S3 sunucusu ile GUI'nin uçtan uca duman testi.

Bu test gerçek motora, lazere veya kameraya erişmez. TCP protokolü, telemetri,
manuel hedef, otomatik mod, PID okuma ve durdurma akışlarını gerçek Qt olay
döngüsü üzerinde doğrular.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

import main as gui

BASE_DIR = Path(__file__).resolve().parent


class KamerasizTestWorker(QObject):
    """GUI sinyal sözleşmesini korur, fiziksel kamera açmaz."""

    frame_ready = pyqtSignal(object, object)
    status_changed = pyqtSignal(str)

    def start(self) -> None:
        self.status_changed.emit("Kamera donanımsız testte atlandı")

    def stop(self) -> None:
        pass

    def wait(self, _milliseconds: int) -> bool:
        return True


def portu_bekle(host: str, port: int, timeout_s: float = 5.0) -> None:
    son_hata: OSError | None = None
    bitis = time.monotonic() + timeout_s
    while time.monotonic() < bitis:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError as hata:
            son_hata = hata
            time.sleep(0.05)
    raise RuntimeError(f"Sahte sunucu başlamadı: {son_hata}")


def olaylari_islet(app: QApplication, sure_s: float) -> None:
    bitis = time.monotonic() + sure_s
    while time.monotonic() < bitis:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    server = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "sahte_sunucu.py")],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        creationflags=creationflags,
    )
    app = QApplication.instance() or QApplication([])
    pencere = None
    try:
        portu_bekle("127.0.0.1", 8080)
        gui.CameraWorker = KamerasizTestWorker
        pencere = gui.AnaPencere()
        pencere.rbWiFi.setChecked(True)
        pencere.leIPAdresi.setText("127.0.0.1")
        pencere.yeniden_baglan_tiklandi()
        olaylari_islet(app, 1.0)

        assert pencere.baglanti_aktif_mi, "GUI telemetri bağlantısını kuramadı."
        assert pencere.lblAzimutDeger.text() != "—", "Azimut telemetrisi işlenmedi."

        pencere.hedefe_git(170.0, 45.0)
        olaylari_islet(app, 0.5)
        assert "Hedef kabul edildi" in pencere.textEditLog.toPlainText()

        pencere.otomatik_mod_tiklandi()
        olaylari_islet(app, 0.5)
        assert pencere.su_anki_mod == "otomatik", "Otomatik mod etkinleşmedi."

        pencere.oku_tiklandi()
        olaylari_islet(app, 0.4)
        assert "PID değerleri ESP32-S3'ten okundu" in pencere.textEditLog.toPlainText()

        pencere.durdur_tiklandi()
        olaylari_islet(app, 0.5)
        assert pencere.su_anki_mod == "manuel", "Durdur sonrası manuel moda dönülmedi."

        print("GUI + sahte ESP32 uçtan uca testi başarılı.")
        return 0
    finally:
        if pencere is not None:
            pencere.close()
            olaylari_islet(app, 0.1)
        server.terminate()
        try:
            server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
            server.communicate(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
