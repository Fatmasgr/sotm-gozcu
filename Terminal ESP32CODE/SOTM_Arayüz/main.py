from __future__ import annotations

import math
import sys
from datetime import datetime
from pathlib import Path

import cv2
from PyQt5 import uic
from PyQt5.QtCore import QSettings, QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
)

import config
from camera_worker import CameraWorker
from haberlesme import Haberlesme, portlari_listele
from hesaplama import hesapla_azimut_elevasyon, piksel_hatasini_aciya_cevir

BASE_DIR = Path(__file__).resolve().parent
UYDU_BOYLAMLARI = {"Türksat 4B": 42.0, "Türksat 5A": 31.0}
TELEMETRI_ZAMAN_ASIMI_S = 1.5
PID_VARSAYILAN = {
    "azimut": {"p": 3.65, "i": 0.58, "d": 0.92},
    "elevasyon": {"p": 3.65, "i": 0.58, "d": 0.92},
}


class AnaPencere(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        uic.loadUi(str(BASE_DIR / "tasarim_2.ui"), self)

        self.haberlesme = Haberlesme()
        self.settings = QSettings("KapsulAtlas", "Gozcu_Kontrol_Paneli")
        self.su_anki_mod = "manuel"
        self.onceki_hedefe_ulasildi = True
        self.hedef_kaybedilme_zamani: datetime | None = None
        self.son_veri_zamani: datetime | None = None
        self.baglanti_aktif_mi = False
        self.son_fault = ""
        self.kamera_kare_sayaci = 0
        self._son_kamera_durumu = ""

        self.son_hesaplanan_azimut = 0.0
        self.son_hesaplanan_elevasyon = 0.0
        self.gecen_sure_saniye = 0
        self.sayac_calisiyor = False

        self._arayuzu_hazirla()
        self._ayarlari_yukle()
        self._sinyalleri_bagla()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.veri_guncelle)
        self.timer.start(50)

        self.sayac_timer = QTimer(self)
        self.sayac_timer.timeout.connect(self.sure_guncelle)
        self.sayac_timer.start(1000)

        self.camera_worker = CameraWorker(parent=self)
        self.camera_worker.frame_ready.connect(self.kamera_karesi_geldi)
        self.camera_worker.status_changed.connect(self.kamera_durumu_degisti)
        self.camera_worker.start()

        self.manuel_mod_tiklandi(gonder=False)
        self.log_yaz("Arayüz hazır. ESP32-S3 bağlantısı bekleniyor.")

    def _arayuzu_hazirla(self) -> None:
        self.lblMcuDeger.setText("ESP32-S3 N16R8")
        self.lblImuDeger.setText("BNO055 - bekleniyor")
        self.lblGpsDeger.setText("Manuel")
        self.lblGucTuketimiDeger.setText("— / 140 W")
        self._portlari_yenile()
        self._pid_tablosunu_yaz(PID_VARSAYILAN)

    def _portlari_yenile(self) -> None:
        secili = self.cboxPort.currentText()
        portlar = portlari_listele()
        self.cboxPort.clear()
        self.cboxPort.addItems(portlar)
        if secili in portlar:
            self.cboxPort.setCurrentText(secili)

    def _ayarlari_yukle(self) -> None:
        kayitli_port = self.settings.value("port", "")
        kayitli_baud = self.settings.value("baud_rate", "115200")
        kayitli_ip = self.settings.value("ip_adresi", "192.168.4.1")
        kayitli_enlem = self.settings.value("enlem", 37.8746, type=float)
        kayitli_boylam = self.settings.value("boylam", 32.4932, type=float)
        kayitli_yukseklik = self.settings.value("yukseklik", 1020.0, type=float)
        kayitli_uydu = self.settings.value("uydu_secimi", "Türksat 4B")

        if kayitli_port:
            index = self.cboxPort.findText(kayitli_port)
            if index >= 0:
                self.cboxPort.setCurrentIndex(index)
        self.cboxBaudRate.setCurrentText(str(kayitli_baud))
        self.leIPAdresi.setText(str(kayitli_ip))
        self.dsboxEnlem.setValue(kayitli_enlem)
        self.dsboxBoylam.setValue(kayitli_boylam)
        self.dsboxYukseklik.setValue(kayitli_yukseklik)

        index = self.cboxUyduSecimi.findText(str(kayitli_uydu))
        if index >= 0:
            self.cboxUyduSecimi.setCurrentIndex(index)

    def _sinyalleri_bagla(self) -> None:
        self.btnYenidenBaglan.clicked.connect(self.yeniden_baglan_tiklandi)
        self.btnYonlendir.clicked.connect(self.yonlendir_tiklandi)
        self.btnDurdur.clicked.connect(self.durdur_tiklandi)
        self.btnManuelMod.clicked.connect(self.manuel_mod_tiklandi)
        self.btnOtomatikMod.clicked.connect(self.otomatik_mod_tiklandi)
        self.btnUyduyaYonlendir.clicked.connect(self.uyduya_yonlendir_tiklandi)
        self.btnOku.clicked.connect(self.oku_tiklandi)
        self.btnUygula.clicked.connect(self.uygula_tiklandi)
        self.btnKaydet.clicked.connect(self.kaydet_tiklandi)
        self.rbUSB.toggled.connect(self.radiobtn_durum_degisme)
        self.rbWiFi.toggled.connect(self.radiobtn_durum_degisme)
        self.radiobtn_durum_degisme()

    def radiobtn_durum_degisme(self) -> None:
        usb = self.rbUSB.isChecked()
        self.cboxPort.setEnabled(usb)
        self.labelPort.setEnabled(usb)
        self.cboxBaudRate.setEnabled(usb)
        self.labelBaudRate.setEnabled(usb)
        self.leIPAdresi.setEnabled(not usb)
        self.labelIPAdresi.setEnabled(not usb)

    def kamera_karesi_geldi(self, frame, veri) -> None:
        if veri.laser_detected:
            self.lblLazerDurum.setText("Lazer Durumu: Aktif")
        elif veri.laser_predicted:
            self.lblLazerDurum.setText("Lazer Durumu: Tahmin Ediliyor")
        else:
            self.lblLazerDurum.setText("Lazer Durumu: Kayıp")

        if veri.cm_distance is not None:
            self.lblHedefDurum.setText(
                f"Hedef Merkeze Uzaklık: {veri.cm_distance:.2f} cm"
            )
        else:
            self.lblHedefDurum.setText("Hedef Merkeze Uzaklık: —")

        self.goruntuyu_goster(frame)
        self.kamera_kare_sayaci += 1
        if (
            self.su_anki_mod == "otomatik"
            and self.baglanti_aktif_mi
            and veri.laser_detected
            and not veri.target_locked
            and self.kamera_kare_sayaci
            % config.CAMERA_CORRECTION_INTERVAL_FRAMES
            == 0
        ):
            self.lazer_duzeltmesi_gonder(veri)

    def kamera_durumu_degisti(self, durum: str) -> None:
        if durum == self._son_kamera_durumu:
            return
        self._son_kamera_durumu = durum
        if "bağlı" not in durum.lower():
            self.lblKamera.setText(durum)
        self.log_yaz(durum, seviye="uyarı" if "kesildi" in durum else "bilgi")

    def goruntuyu_goster(self, frame) -> None:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        yukseklik, genislik, kanal = rgb_frame.shape
        qimg = QImage(
            rgb_frame.data,
            genislik,
            yukseklik,
            kanal * genislik,
            QImage.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(qimg)
        self.lblKamera.setPixmap(
            pixmap.scaled(
                self.lblKamera.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def lazer_duzeltmesi_gonder(self, veri) -> None:
        if veri.error_x is None or veri.error_y is None:
            return
        duzeltme_az, duzeltme_el = piksel_hatasini_aciya_cevir(
            veri.error_x, veri.error_y, config.FRAME_WIDTH, config.FRAME_HEIGHT
        )
        self._komut_gonder(
            {
                "komut": "duzelt",
                "delta_azimuth": round(duzeltme_az, 4),
                "delta_elevation": round(duzeltme_el, 4),
            },
            hata_logla=False,
        )

    def yeniden_baglan_tiklandi(self) -> None:
        self.baglanti_aktif_mi = False
        self.son_veri_zamani = None
        if self.rbUSB.isChecked():
            self._portlari_yenile()
            port_adi = self.cboxPort.currentText()
            baud_rate = int(self.cboxBaudRate.currentText())
            self.log_yaz(
                f"USB bağlantısı deneniyor: Port={port_adi}, Baud={baud_rate}"
            )
            sonuc = self.haberlesme.baglan_usb(port_adi, baud_rate)
        elif self.rbWiFi.isChecked():
            ip_adresi = self.leIPAdresi.text().strip()
            self.log_yaz(
                f"Wi-Fi bağlantısı deneniyor: {ip_adresi}:8080"
            )
            sonuc = self.haberlesme.baglan_wifi(ip_adresi)
        else:
            self.log_yaz(
                "Lütfen USB veya Wi-Fi bağlantı türünü seçin.",
                seviye="uyarı",
                mesaj_kutusu_goster=True,
            )
            return

        if sonuc:
            self.lblBaglantiDurum.setText("● Bağlantı: Telemetri bekleniyor")
            self.lblBaglantiDurum.setStyleSheet(
                "color: #d97706; font-size: 13px;"
            )
            self.log_yaz("Taşıma bağlantısı kuruldu; ESP32-S3 telemetrisi bekleniyor.")
            self._komut_gonder({"komut": "ping"}, hata_logla=False)
            self._komut_gonder(
                {"komut": "mod_degistir", "mod": self.su_anki_mod},
                hata_logla=False,
            )
        else:
            self._baglantisiz_arayuz()
            self.log_yaz(
                self.haberlesme.son_hata or "Bağlantı başarısız.",
                seviye="hata",
            )

    def veri_guncelle(self) -> None:
        mesaj_sayisi = 0
        while mesaj_sayisi < 50:
            veri = self.haberlesme.veri_oku()
            if veri is None:
                break
            mesaj_sayisi += 1
            self.son_veri_zamani = datetime.now()
            mesaj_tipi = veri.get("type", "telemetry")
            if mesaj_tipi == "telemetry":
                self._telemetriyi_isle(veri)
            elif mesaj_tipi == "pid":
                self._pid_mesajini_isle(veri)
            elif mesaj_tipi == "ack":
                self._ack_mesajini_isle(veri)
            elif mesaj_tipi in {"event", "hello"}:
                self.log_yaz(str(veri.get("message", mesaj_tipi)))

        self.baglanti_kontrol_et()

    @staticmethod
    def _ilk_deger(veri: dict, *anahtarlar, varsayilan=0.0):
        for anahtar in anahtarlar:
            if anahtar in veri:
                return veri[anahtar]
        return varsayilan

    def _telemetriyi_isle(self, veri: dict) -> None:
        self._bagli_arayuz()
        azimut = self._ilk_deger(veri, "azimut", "Azimut: ")
        elevasyon = self._ilk_deger(veri, "elevasyon", "Elevasyon: ")
        roll = self._ilk_deger(veri, "roll", "roll ")
        pitch = self._ilk_deger(veri, "pitch", "pitch ")
        yaw = self._ilk_deger(veri, "yaw", "yaw ")
        hata = self._ilk_deger(veri, "hata_acisi", varsayilan=0.0)

        self.lblAzimutDeger.setText(self._aci_metni(azimut))
        self.lblElevasyonDeger.setText(self._aci_metni(elevasyon))
        self.lblRollDeger.setText(self._aci_metni(roll))
        self.lblPitchDeger.setText(self._aci_metni(pitch))
        self.lblYawDeger.setText(self._aci_metni(yaw))
        self.lblHataAcisiDeger.setText(self._aci_metni(hata))

        imu_ok = bool(veri.get("imu_ok", False))
        encoder_ok = bool(
            veri.get("encoder_az_ok", False) and veri.get("encoder_el_ok", False)
        )
        self.lblImuDeger.setText("BNO055 - OK" if imu_ok else "BNO055 - HATA")
        self.lblGpsDeger.setText("Manuel")
        guc = veri.get("guc_tuketimi_w")
        self.lblGucTuketimiDeger.setText(
            f"{float(guc):.1f} / 140 W" if isinstance(guc, (int, float)) else "— / 140 W"
        )

        hedefe_ulasildi = bool(veri.get("hedefe_ulasildi", False))
        if hedefe_ulasildi != self.onceki_hedefe_ulasildi:
            if not hedefe_ulasildi:
                self.hedef_kaybedilme_zamani = datetime.now()
                self.log_yaz("Hedef kaybedildi; yeniden yönelim başladı.", "uyarı")
            elif self.hedef_kaybedilme_zamani is not None:
                saniye = (
                    datetime.now() - self.hedef_kaybedilme_zamani
                ).total_seconds()
                self.log_yaz(f"Hedef yeniden bulundu. Süre: {saniye:.2f} saniye")
            self.onceki_hedefe_ulasildi = hedefe_ulasildi

        fault = str(veri.get("fault", "") or "")
        if fault and fault != self.son_fault:
            self.log_yaz(f"ESP32 güvenlik hatası: {fault}", "hata", True)
        self.son_fault = fault

        if not encoder_ok and not fault:
            self.log_yaz("Enkoder telemetrisi geçersiz.", "uyarı")

    @staticmethod
    def _aci_metni(deger) -> str:
        try:
            sayi = float(deger)
            return f"{sayi:.2f}°" if math.isfinite(sayi) else "—"
        except (TypeError, ValueError):
            return "—"

    def _ack_mesajini_isle(self, veri: dict) -> None:
        komut = veri.get("cmd", "komut")
        mesaj = veri.get("message", "")
        if veri.get("ok", False):
            if komut == "dur":
                self.manuel_mod_tiklandi(gonder=False)
            if komut not in {"ping", "duzelt"}:
                self.log_yaz(f"{komut}: {mesaj or 'onaylandı'}")
        else:
            if komut == "mod_degistir" and self.su_anki_mod == "otomatik":
                self.manuel_mod_tiklandi(gonder=False)
            self.log_yaz(f"{komut} reddedildi: {mesaj}", "hata")

    def _pid_mesajini_isle(self, veri: dict) -> None:
        pid = veri.get("pid")
        if not isinstance(pid, dict):
            pid = {
                "azimut": {
                    "p": veri.get("azimut_p", 0),
                    "i": veri.get("azimut_i", 0),
                    "d": veri.get("azimut_d", 0),
                },
                "elevasyon": {
                    "p": veri.get("elevasyon_p", 0),
                    "i": veri.get("elevasyon_i", 0),
                    "d": veri.get("elevasyon_d", 0),
                },
            }
        self._pid_tablosunu_yaz(pid)
        self.log_yaz("PID değerleri ESP32-S3'ten okundu.")

    def _pid_tablosunu_yaz(self, pid: dict) -> None:
        for satir, eksen in enumerate(("azimut", "elevasyon")):
            degerler = pid.get(eksen, {})
            for sutun, anahtar in enumerate(("p", "i", "d")):
                self.tablePID.setItem(
                    satir,
                    sutun,
                    QTableWidgetItem(str(degerler.get(anahtar, 0))),
                )

    def _bagli_arayuz(self) -> None:
        self.lblSistemBaglantisi.setText("● Sistem Bağlı  ")
        self.lblSistemBaglantisi.setStyleSheet(
            "color: green; border: none; font-size: 14px;"
        )
        self.lblBaglantiDurum.setText("● Bağlantı: Bağlı")
        self.lblBaglantiDurum.setStyleSheet("color: green; font-size: 13px;")
        if not self.baglanti_aktif_mi:
            self.baglanti_aktif_mi = True
            self.log_yaz("ESP32-S3 telemetrisi alındı; sistem çevrimiçi.")
            self.btnManuelMod.setEnabled(True)
            self.btnOtomatikMod.setEnabled(True)

    def _baglantisiz_arayuz(self) -> None:
        self.baglanti_aktif_mi = False
        for label in (
            self.lblAzimutDeger,
            self.lblElevasyonDeger,
            self.lblRollDeger,
            self.lblPitchDeger,
            self.lblYawDeger,
            self.lblHataAcisiDeger,
        ):
            label.setText("—")
        self.lblSistemBaglantisi.setText("● Sistem Bağlı Değil  ")
        self.lblSistemBaglantisi.setStyleSheet(
            "color: #dc2626; border: none; font-size: 14px;"
        )
        self.lblBaglantiDurum.setText("● Bağlantı: Bağlı Değil")
        self.lblBaglantiDurum.setStyleSheet("color: #dc2626; font-size: 13px;")

    def baglanti_kontrol_et(self) -> None:
        if not self.haberlesme.bagli:
            if self.baglanti_aktif_mi:
                self.log_yaz(
                    self.haberlesme.son_hata
                    or "Arayüz bağlantısı kesildi; fiziksel sistemi telemetriden doğrulayın.",
                    "hata",
                )
                self._baglantisiz_arayuz()
            return
        if self.son_veri_zamani is None:
            return
        gecen = (datetime.now() - self.son_veri_zamani).total_seconds()
        if gecen > TELEMETRI_ZAMAN_ASIMI_S and self.baglanti_aktif_mi:
            self.log_yaz("Telemetri zaman aşımı; bağlantı geçersiz sayıldı.", "hata")
            self._baglantisiz_arayuz()

    def sure_guncelle(self) -> None:
        if not self.sayac_calisiyor:
            return
        self.gecen_sure_saniye += 1
        dakika, saniye = divmod(self.gecen_sure_saniye, 60)
        if self.gecen_sure_saniye >= 300:
            self.lblStabilizasyon.setText("Stabilizasyon: 5 dk TEST TAMAMLANDI")
            self.lblStabilizasyon.setStyleSheet(
                "color: green; font-size: 13px; font-weight: 600;"
            )
            self.sayaci_durdur()
        else:
            self.lblStabilizasyon.setText(
                f"Stabilizasyon: AKTİF {dakika:02d}:{saniye:02d} / 05:00"
            )
            self.lblStabilizasyon.setStyleSheet(
                "color: green; font-size: 13px;"
            )

    def sayaci_baslat(self) -> None:
        self.gecen_sure_saniye = 0
        self.sayac_calisiyor = True

    def sayaci_durdur(self) -> None:
        self.sayac_calisiyor = False

    def hesapla_tiklandi(self) -> bool:
        secilen_uydu = self.cboxUyduSecimi.currentText()
        if secilen_uydu not in UYDU_BOYLAMLARI:
            self.log_yaz("Geçerli bir uydu seçilmedi.", "uyarı", True)
            return False
        try:
            azimut, elevasyon = hesapla_azimut_elevasyon(
                self.dsboxEnlem.value(),
                self.dsboxBoylam.value(),
                UYDU_BOYLAMLARI[secilen_uydu],
                self.dsboxYukseklik.value(),
            )
        except ValueError as hata:
            QMessageBox.warning(self, "Hesaplama Hatası", str(hata))
            return False
        if elevasyon < 0.0:
            self.log_yaz(
                f"{secilen_uydu} ufkun altında (El={elevasyon:.2f}°).",
                "uyarı",
                True,
            )
            return False
        self.son_hesaplanan_azimut = azimut
        self.son_hesaplanan_elevasyon = elevasyon
        self.log_yaz(f"Hesaplandı: Az={azimut:.2f}°, El={elevasyon:.2f}°")
        return True

    def yonlendir_tiklandi(self) -> None:
        self.hedefe_git(self.dsboxAzimut.value(), self.dsboxElevasyon.value())

    def uyduya_yonlendir_tiklandi(self) -> None:
        if self.hesapla_tiklandi():
            self.hedefe_git(
                self.son_hesaplanan_azimut, self.son_hesaplanan_elevasyon
            )

    def hedefe_git(self, azimut_degeri: float, elevasyon_degeri: float) -> None:
        if self.su_anki_mod != "manuel":
            QMessageBox.warning(
                self, "Mod Hatası", "Önce Manuel Mod'a geçmelisiniz."
            )
            return
        if not 0.0 <= azimut_degeri < 360.0 or not 0.0 <= elevasyon_degeri <= 90.0:
            self.log_yaz("Hedef açıları izin verilen hareket zarfı dışında.", "uyarı", True)
            return
        if self._komut_gonder(
            {
                "komut": "git",
                "azimut": round(azimut_degeri, 3),
                "elevasyon": round(elevasyon_degeri, 3),
            }
        ):
            self.log_yaz(
                f"Yönelim komutu: Az={azimut_degeri:.2f}°, "
                f"El={elevasyon_degeri:.2f}°"
            )

    def durdur_tiklandi(self) -> None:
        if self._komut_gonder({"komut": "dur"}):
            self.sayaci_durdur()
            self.log_yaz("Yazılımsal DURDUR komutu gönderildi.", "uyarı")

    def manuel_mod_tiklandi(self, _checked=False, gonder: bool = True) -> None:
        self.su_anki_mod = "manuel"
        if gonder:
            self._komut_gonder(
                {"komut": "mod_degistir", "mod": "manuel"}, hata_logla=False
            )
        self.lblStabilizasyon.setStyleSheet(
            "color: #cccccc; font-size: 13px;"
        )
        self.lblStabilizasyon.setText("Stabilizasyon: PASİF")
        self.gbUyduHesaplama.setEnabled(True)
        self.buton_aktif_yap(self.btnUyduyaYonlendir)
        self.dsboxAzimut.setEnabled(True)
        self.labelAzimutManuel.setEnabled(True)
        self.dsboxElevasyon.setEnabled(True)
        self.labelElevasyonManuel.setEnabled(True)
        self.buton_aktif_yap(self.btnYonlendir)
        self.sayaci_durdur()
        self.btnManuelMod.setStyleSheet(
            "background-color: #2563eb; color: white; border-radius: 10px; "
            "border: none; padding: 8px 15px; font-size: 13px;"
        )
        self.btnOtomatikMod.setStyleSheet(
            "background-color: white; color: black; border-radius: 10px; "
            "border: 1px solid #cccccc; padding: 8px 15px; font-size: 13px;"
        )
        if gonder:
            self.log_yaz("Manuel moda geçildi.")

    def otomatik_mod_tiklandi(self, _checked=False) -> None:
        if not self.baglanti_aktif_mi:
            self.log_yaz("Otomatik mod için aktif ESP32 telemetrisi gerekir.", "uyarı")
            return
        self.su_anki_mod = "otomatik"
        self._komut_gonder({"komut": "mod_degistir", "mod": "otomatik"})
        self.gbUyduHesaplama.setEnabled(False)
        self.buton_pasif_yap(self.btnUyduyaYonlendir)
        self.dsboxAzimut.setEnabled(False)
        self.labelAzimutManuel.setEnabled(False)
        self.dsboxElevasyon.setEnabled(False)
        self.labelElevasyonManuel.setEnabled(False)
        self.buton_pasif_yap(self.btnYonlendir)
        self.sayaci_baslat()
        self.btnOtomatikMod.setStyleSheet(
            "background-color: #2563eb; color: white; border-radius: 10px; "
            "border: none; padding: 8px 15px; font-size: 13px;"
        )
        self.btnManuelMod.setStyleSheet(
            "background-color: white; color: black; border-radius: 10px; "
            "border: 1px solid #cccccc; padding: 8px 15px; font-size: 13px;"
        )
        self.log_yaz("Otomatik stabilizasyon modu istendi.")

    @staticmethod
    def buton_aktif_yap(buton) -> None:
        buton.setEnabled(True)
        buton.setGraphicsEffect(None)

    @staticmethod
    def buton_pasif_yap(buton) -> None:
        buton.setEnabled(False)
        efekt = QGraphicsOpacityEffect()
        efekt.setOpacity(0.4)
        buton.setGraphicsEffect(efekt)

    def oku_tiklandi(self) -> None:
        if self._komut_gonder({"komut": "pid_oku"}):
            self.log_yaz("PID okuma isteği gönderildi.")

    def pid_gonder(self, kalici: bool) -> None:
        try:
            degerler = [
                float(self.tablePID.item(satir, sutun).text())
                for satir in range(2)
                for sutun in range(3)
            ]
        except (AttributeError, TypeError, ValueError) as hata:
            self.log_yaz(f"PID tablosunda hatalı değer var: {hata}", "uyarı", True)
            return
        if not all(math.isfinite(deger) and 0.0 <= deger <= 100.0 for deger in degerler):
            self.log_yaz("PID değerleri 0 ile 100 arasında olmalıdır.", "uyarı", True)
            return

        az_p, az_i, az_d, el_p, el_i, el_d = degerler
        komut = {
            "komut": "pid_uygula",
            "kalici": kalici,
            "azimut": {"p": az_p, "i": az_i, "d": az_d},
            "elevasyon": {"p": el_p, "i": el_i, "d": el_d},
        }
        if self._komut_gonder(komut):
            self.log_yaz(
                "PID değerleri kalıcı kayıt için gönderildi."
                if kalici
                else "PID değerleri anlık uygulama için gönderildi."
            )

    def uygula_tiklandi(self) -> None:
        self.pid_gonder(kalici=False)

    def kaydet_tiklandi(self) -> None:
        self.pid_gonder(kalici=True)

    def _komut_gonder(self, komut: dict, hata_logla: bool = True) -> bool:
        sonuc = self.haberlesme.veri_gonder(komut)
        if not sonuc and hata_logla:
            self.log_yaz(
                self.haberlesme.son_hata or "Komut gönderilemedi.", "hata"
            )
        return sonuc

    def log_yaz(
        self, mesaj: str, seviye: str = "bilgi", mesaj_kutusu_goster: bool = False
    ) -> None:
        renk = {"hata": "#dc2626", "uyarı": "#d97706"}.get(seviye, "#111827")
        saat = datetime.now().strftime("%H:%M:%S")
        html = f"<span style='color:{renk};'>[{saat}] {mesaj}</span><br>"
        cursor = self.textEditLog.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        self.textEditLog.setTextCursor(cursor)
        self.textEditLog.ensureCursorVisible()
        if mesaj_kutusu_goster:
            QMessageBox.warning(self, "Uyarı", mesaj)

        if self.textEditLog.document().blockCount() > 500:
            cursor = self.textEditLog.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def closeEvent(self, event) -> None:
        self.camera_worker.stop()
        self.camera_worker.wait(2500)
        self.haberlesme.baglantiyi_kes()

        self.settings.setValue("port", self.cboxPort.currentText())
        self.settings.setValue("baud_rate", self.cboxBaudRate.currentText())
        self.settings.setValue("ip_adresi", self.leIPAdresi.text())
        self.settings.setValue("enlem", self.dsboxEnlem.value())
        self.settings.setValue("boylam", self.dsboxBoylam.value())
        self.settings.setValue("yukseklik", self.dsboxYukseklik.value())
        self.settings.setValue("uydu_secimi", self.cboxUyduSecimi.currentText())
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec_())
