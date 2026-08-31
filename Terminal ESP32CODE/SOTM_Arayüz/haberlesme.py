"""ESP32-S3 ile USB veya TCP üzerinden satır tabanlı JSON haberleşmesi."""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any, Optional

import serial
import serial.tools.list_ports

WIFI_PORT = 8080
MAX_LINE_BYTES = 16_384


class Haberlesme:
    """Arayüzü bloklamayan, parçalı TCP/seri paketlerini birleştiren istemci."""

    def __init__(self) -> None:
        self.baglanti: Optional[Any] = None
        self.baglanti_tipi: Optional[str] = None
        self.son_hata: Optional[str] = None
        self.son_alim_zamani: Optional[float] = None

        self._rx_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=500)
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._send_lock = threading.Lock()
        self._state_lock = threading.Lock()

    @property
    def bagli(self) -> bool:
        with self._state_lock:
            return self.baglanti is not None

    def _baglantiyi_ata(self, baglanti: Any, baglanti_tipi: str) -> None:
        self.baglantiyi_kes()
        with self._state_lock:
            self.baglanti = baglanti
            self.baglanti_tipi = baglanti_tipi
            self.son_hata = None
            self.son_alim_zamani = None
        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._okuyucu_dongusu,
            name=f"sotm-{baglanti_tipi}-reader",
            daemon=True,
        )
        self._reader_thread.start()

    def baglan_usb(self, port_adi: str, baud_rate: int) -> bool:
        if not port_adi:
            self.son_hata = "Seri port seçilmedi."
            return False
        try:
            baglanti = serial.Serial(
                port=port_adi,
                baudrate=baud_rate,
                timeout=0.1,
                write_timeout=0.5,
            )
            baglanti.reset_input_buffer()
            self._baglantiyi_ata(baglanti, "usb")
            return True
        except (OSError, serial.SerialException, ValueError) as hata:
            self.son_hata = f"USB bağlantı hatası: {hata}"
            return False

    # Eski arayüz/test kodlarıyla geriye uyumluluk.
    def baglan(self, port_adi: str, baud_rate: int) -> bool:
        return self.baglan_usb(port_adi, baud_rate)

    def baglan_wifi(self, ip_adresi: str, port: int = WIFI_PORT) -> bool:
        if not ip_adresi:
            self.son_hata = "ESP32 IP adresi girilmedi."
            return False
        try:
            baglanti = socket.create_connection((ip_adresi, port), timeout=3.0)
            baglanti.settimeout(0.2)
            baglanti.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._baglantiyi_ata(baglanti, "wifi")
            return True
        except (OSError, ValueError) as hata:
            self.son_hata = f"Wi-Fi bağlantı hatası: {hata}"
            return False

    def baglantiyi_kes(self) -> bool:
        self._stop_event.set()
        with self._state_lock:
            baglanti = self.baglanti
            self.baglanti = None
            self.baglanti_tipi = None

        if baglanti is not None:
            try:
                baglanti.close()
            except (OSError, serial.SerialException):
                pass

        okuyucu = self._reader_thread
        if okuyucu and okuyucu.is_alive() and okuyucu is not threading.current_thread():
            okuyucu.join(timeout=0.5)
        self._reader_thread = None
        return True

    def veri_gonder(self, mesaj: dict[str, Any]) -> bool:
        if not isinstance(mesaj, dict):
            self.son_hata = "Gönderilecek mesaj JSON nesnesi (dict) olmalıdır."
            return False

        with self._state_lock:
            baglanti = self.baglanti
            baglanti_tipi = self.baglanti_tipi
        if baglanti is None:
            self.son_hata = "Aktif bağlantı yok."
            return False

        paket = (
            json.dumps(mesaj, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        try:
            with self._send_lock:
                if baglanti_tipi == "usb":
                    baglanti.write(paket)
                    baglanti.flush()
                elif baglanti_tipi == "wifi":
                    baglanti.sendall(paket)
                else:
                    raise RuntimeError("Bilinmeyen bağlantı türü.")
            return True
        except (OSError, serial.SerialException, RuntimeError) as hata:
            self.son_hata = f"Veri gönderme hatası: {hata}"
            self._baglanti_koptu()
            return False

    def veri_oku(self) -> Optional[dict[str, Any]]:
        """Bir mesajı bloklamadan döndürür; kuyruk boşsa ``None`` verir."""
        try:
            return self._rx_queue.get_nowait()
        except queue.Empty:
            return None

    def _baglanti_koptu(self) -> None:
        self._stop_event.set()
        with self._state_lock:
            baglanti = self.baglanti
            self.baglanti = None
            self.baglanti_tipi = None
        if baglanti is not None:
            try:
                baglanti.close()
            except (OSError, serial.SerialException):
                pass

    def _oku(self, baglanti: Any, baglanti_tipi: str) -> bytes:
        if baglanti_tipi == "usb":
            return baglanti.read(1024)
        return baglanti.recv(4096)

    def _okuyucu_dongusu(self) -> None:
        buffer = bytearray()
        while not self._stop_event.is_set():
            with self._state_lock:
                baglanti = self.baglanti
                baglanti_tipi = self.baglanti_tipi
            if baglanti is None or baglanti_tipi is None:
                return

            try:
                parca = self._oku(baglanti, baglanti_tipi)
                if not parca:
                    if baglanti_tipi == "wifi":
                        raise ConnectionError("ESP32 bağlantıyı kapattı.")
                    continue
                buffer.extend(parca)
                if len(buffer) > MAX_LINE_BYTES * 2:
                    raise ValueError("Alım tamponu sınırı aşıldı.")

                while b"\n" in buffer:
                    satir, _, kalan = buffer.partition(b"\n")
                    buffer = bytearray(kalan)
                    satir = satir.strip()
                    if not satir:
                        continue
                    if len(satir) > MAX_LINE_BYTES:
                        raise ValueError("JSON satırı çok uzun.")
                    try:
                        veri = json.loads(satir.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        # ESP32 açılış günlükleri veya bozuk tek satır protokolü
                        # tamamen durdurmamalıdır.
                        continue
                    if not isinstance(veri, dict):
                        continue
                    self.son_alim_zamani = time.monotonic()
                    try:
                        self._rx_queue.put_nowait(veri)
                    except queue.Full:
                        try:
                            self._rx_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self._rx_queue.put_nowait(veri)
            except (socket.timeout, serial.SerialTimeoutException):
                continue
            except (OSError, serial.SerialException, ConnectionError, ValueError) as hata:
                self.son_hata = f"Bağlantı okuma hatası: {hata}"
                self._baglanti_koptu()
                return


class SahteHaberlesme:
    """Donanım olmadan arayüz geliştirmek için protokol uyumlu simülatör."""

    def __init__(self) -> None:
        self.azimut_deger = 163.0
        self.elevasyon_deger = 42.0
        self._bagli = False
        self._mod = "manuel"

    @property
    def bagli(self) -> bool:
        return self._bagli

    def baglan(self, _port_adi: str, _baud_rate: int) -> bool:
        self._bagli = True
        return True

    baglan_usb = baglan

    def baglan_wifi(self, _ip_adresi: str, _port: int = WIFI_PORT) -> bool:
        self._bagli = True
        return True

    def baglantiyi_kes(self) -> bool:
        self._bagli = False
        return True

    def veri_gonder(self, mesaj: dict[str, Any]) -> bool:
        if mesaj.get("komut") == "mod_degistir":
            self._mod = str(mesaj.get("mod", "manuel"))
        return self._bagli

    def veri_oku(self) -> Optional[dict[str, Any]]:
        if not self._bagli:
            return None
        import random

        self.azimut_deger += random.uniform(-0.15, 0.15)
        self.elevasyon_deger += random.uniform(-0.08, 0.08)
        return {
            "type": "telemetry",
            "protocol": 1,
            "mode": self._mod,
            "state": "tracking" if self._mod == "otomatik" else "ready",
            "azimut": round(self.azimut_deger, 2),
            "elevasyon": round(self.elevasyon_deger, 2),
            "roll": round(random.uniform(-0.4, 0.4), 2),
            "pitch": round(random.uniform(-0.4, 0.4), 2),
            "yaw": round(random.uniform(-0.4, 0.4), 2),
            "hata_acisi": 0.2,
            "hedefe_ulasildi": True,
            "imu_ok": True,
            "encoder_az_ok": True,
            "encoder_el_ok": True,
            "motors_enabled": self._mod == "otomatik",
            "fault": "",
        }


def portlari_listele() -> list[str]:
    return [port.device for port in serial.tools.list_ports.comports()]
