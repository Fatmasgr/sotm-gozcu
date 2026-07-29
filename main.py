import sys, time
from PyQt5.QtWidgets import QApplication, QMainWindow,QMessageBox, QTableWidgetItem
from PyQt5.QtCore import QTimer, QSettings
from PyQt5 import uic
from haberlesme import Haberlesme, SahteHaberlesme, portlari_listele
from hesaplama import hesapla_azimut_elevasyon, piksel_hatasini_aciya_cevir
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from datetime import datetime

#görüntü işleme için ekledik.
import cv2
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
import config
from laser_pipeline import LaserTargetSystem

UYDU_BOYLAMLARI = {"Türksat 4B": 42.0, "Türksat 5A": 31.0}

#sistemi gerçekten test ederek bu açıların kontrol edilmesi gerek
#görüntü işlemedeki geri dönüş açılarını kullanmamız için 
KP_AZIMUT = 0.02
KP_ELEVASYON = 0.02

class AnaPencere(QMainWindow):
    def __init__(self):

        super().__init__()
        uic.loadUi("tasarim_2.ui", self)

        self.haberlesme = Haberlesme()
        #self.haberlesme = SahteHaberlesme()
        self.settings = QSettings("KapsulAtlas", "Gozcu_Kontrol_Paneli")

        self.timer = QTimer()
        self.timer.timeout.connect(self.veri_guncelle)
        self.timer.start(100)

        self.sayac_timer = QTimer()
        self.sayac_timer.timeout.connect(self.sure_guncelle)
        self.sayac_timer.start(1000)
        self.gecen_sure_saniye = 0
        self.sayac_calisiyor = False

        #görüntü işleme için ekledik 
        self.kamera = cv2.VideoCapture(config.CAMERA_INDEX)
        self.kamera_kare_sayaci = 0
        self.lazer_sistem = LaserTargetSystem()
        ##görüntü işleme için ekledik 
        self.kamera_timer = QTimer()
        self.kamera_timer.timeout.connect(self.kamerayi_guncelle)
        self.kamera_timer.start(33)

        self.cboxPort.clear()
        self.cboxPort.addItems(portlari_listele())

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

        #self.sure_guncelle()
        self.onceki_hedefe_ulasildi = True
        self.hedef_kaybedilme_zamani = None
        self.son_veri_zamani = None
        self.baglanti_aktif_mi = False

        #bunlar sonra değişebilir.
        self.manuel_mod_tiklandi()
        self.son_hesaplanan_azimut = 0
        self.son_hesaplanan_elevasyon = 0

        #kaydedilen verileri tekrar göstermeyi sağlar.
        kayitli_port = self.settings.value("port", "")
        kayitli_baud = self.settings.value("baud_rate", "115200")
        kayitli_ip = self.settings.value("ip_adresi", "")
        kayitli_enlem = self.settings.value("enlem", 0.0, type=float)
        kayitli_boylam = self.settings.value("boylam", 0.0, type=float)
        kayitli_yukseklik = self.settings.value("yukseklik", 0.0, type=float)
        kayitli_uydu = self.settings.value("uydu_secimi", "")

        if kayitli_port:
            index = self.cboxPort.findText(kayitli_port)
            if index >= 0:
                self.cboxPort.setCurrentIndex(index)

        self.cboxBaudRate.setCurrentText(kayitli_baud)
        self.leIPAdresi.setText(kayitli_ip)
        self.dsboxEnlem.setValue(kayitli_enlem)
        self.dsboxBoylam.setValue(kayitli_boylam)
        self.dsboxYukseklik.setValue(kayitli_yukseklik)

        if kayitli_uydu:
            index = self.cboxUyduSecimi.findText(kayitli_uydu)
            if index >= 0:
                self.cboxUyduSecimi.setCurrentIndex(index)

    def radiobtn_durum_degisme(self):
        if self.rbUSB.isChecked():

            self.cboxPort.setEnabled(True)
            self.labelPort.setEnabled(True)

            self.cboxBaudRate.setEnabled(True)
            self.labelBaudRate.setEnabled(True)

            self.leIPAdresi.setEnabled(False)
            self.labelIPAdresi.setEnabled(False)
            
        else:

            self.cboxPort.setEnabled(False)
            self.labelPort.setEnabled(False)

            self.cboxBaudRate.setEnabled(False)
            self.labelBaudRate.setEnabled(False)

            self.leIPAdresi.setEnabled(True)
            self.labelIPAdresi.setEnabled(True)

    #görüntü işleme için ekledik
    def kamerayi_guncelle(self):
        ret, frame = self.kamera.read()
        if not ret:
            return

        frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
        frame, veri = self.lazer_sistem.process_frame(frame)

        if veri.laser_detected:
            self.lblLazerDurum.setText("Lazer Durumu: Aktif")
        elif veri.laser_predicted:
            self.lblLazerDurum.setText("Lazer Durumu: Tahmin Ediliyor")
        else:
            self.lblLazerDurum.setText("Lazer Durumu: Kayıp")

        if veri.cm_distance is not None:
            self.lblHedefDurum.setText(f"Hedef Merkeze Uzaklık: {veri.cm_distance:.2f} cm")
        else:
            self.lblHedefDurum.setText("Hedef Merkeze Uzaklık: —")

        self.goruntuyu_goster(frame)

        self.kamera_kare_sayaci += 1
        if self.su_anki_mod == "otomatik" and self.kamera_kare_sayaci % 3 == 0:
            self.lazer_duzeltmesi_gonder(veri)

    #görüntü işleme için yaptık
    def goruntuyu_goster(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        yukseklik, genislik, kanal = rgb_frame.shape
        bayt_basina_satir = kanal * genislik

        qimg = QImage(rgb_frame.data, genislik, yukseklik, bayt_basina_satir, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.lblKamera.setPixmap(
            pixmap.scaled(self.lblKamera.width(), self.lblKamera.height(), Qt.KeepAspectRatio)
        )
    #görüntü işleme için yazdık
    def lazer_duzeltmesi_gonder(self, veri):
        if veri.laser_x is None:
            return

        if veri.target_locked:
            return

        duzeltme_az, duzeltme_el = piksel_hatasini_aciya_cevir(veri.error_x, veri.error_y)

        komut = { #stm32 kodlayanla konuşulmalı.
        "komut": "duzelt",
        "delta_azimuth": duzeltme_az,
        "delta_elevation": duzeltme_el
        }
        self.haberlesme.veri_gonder(komut)

    def yeniden_baglan_tiklandi(self):

        if self.rbUSB.isChecked():
            port_adi = self.cboxPort.currentText()
            baud_rate = int(self.cboxBaudRate.currentText())

            self.log_yaz(f"USB Bağlantısı deneniyor: Port={port_adi}, Baud={baud_rate}")
            #sonuc = self.haberlesme.baglan_usb(port_adi,baud_rate)
            sonuc = self.haberlesme.baglan(port_adi,baud_rate)

        elif self.rbWiFi.isChecked():
            ip_adresi = self.leIPAdresi.text()

            self.log_yaz(f"Wi-Fi Bağlantısı deneniyor: IP Adresi={ip_adresi}")
            sonuc = self.haberlesme.baglan_wifi(ip_adresi)
        else:
            self.log_yaz("Lütfen bir bağlantı türü seçin (USB/Wi-Fi).", seviye="uyarı", mesaj_kutusu_goster=True)
            sonuc = False
        
        if sonuc:
            self.lblBaglantiDurum.setText("● Bağlantı: Bağlı")
            self.lblBaglantiDurum.setStyleSheet("color: green; font-size: 13px;")

            self.log_yaz("Bağlantı Başarılı!")
        else:
            self.lblBaglantiDurum.setText("● Bağlantı: Bağlı Değil")
            self.lblBaglantiDurum.setStyleSheet("color: #dc2626; font-size: 13px;")

            self.log_yaz("Bağlantı Başarısız!", seviye="hata")

    def veri_guncelle(self):
        veri = self.haberlesme.veri_oku()
        hedefe_ulasildi = veri.get("hedefe_ulasildi", True) #stm32 yapanla konuşulacak.

        if hedefe_ulasildi != self.onceki_hedefe_ulasildi:
            if not hedefe_ulasildi:
                self.hedef_kaybedilme_zamani = datetime.now()
                self.log_yaz("Hedef kaybedildi, yeniden yönelim başladı.", seviye="uyarı")
            else:
                if self.hedef_kaybedilme_zamani is not None:
                    gecen_sure = datetime.now() - self.hedef_kaybedilme_zamani
                    saniye = gecen_sure.total_seconds()
                    self.log_yaz(f"Hedef yeniden bulundu. Süre: {saniye:.2f} saniye")
    
            self.onceki_hedefe_ulasildi = hedefe_ulasildi

        if veri is None:
            self.baglanti_kontrol_et()
            return

        self.son_veri_zamani = datetime.now()
        self.lblSistemBaglantisi.setText("● Sistem Bağlı  ")
        self.lblSistemBaglantisi.setStyleSheet("color: green; border: none; font-size: 14px;")

        if not self.baglanti_aktif_mi:
            self.baglanti_aktif_mi = True
            self.log_yaz("Bağlantı yeniden sağlandı, sistem normale döndü.")
            self.btnManuelMod.setEnabled(True)
            self.btnOtomatikMod.setEnabled(True)

        self.lblAzimutDeger.setText(str(veri.get("Azimut: ", 0)))#Bu isimleri stm32 yi kodlayan kişilerden almamız gerekiyor.
        self.lblElevasyonDeger.setText(str(veri.get("Elevasyon: ", 0)))
        # Eğer stm32 kodlayan roll, pitch ve yaw varsa aynı şekilde onlarıda almalısın.

    def baglanti_kontrol_et(self):
        if self.son_veri_zamani is None:
            return
        gecen_sure = (datetime.now() - self.son_veri_zamani).total_seconds()
        if  gecen_sure > 1.0 and self.baglanti_aktif_mi:
            self.baglanti_aktif_mi =False

            self.lblAzimutDeger.setText("—--")
            self.lblElevasyonDeger.setText("—--")
            #yine eğer stm32 de roll pitch yaw varsa onları da aynen ekle.
            #self.lblRollDeger.setText("---")
            #self.lblPitchDeger.setText("---")
            #self.lblYawDeger.setText("---")
            #self.lblHataAcisiDeger.setText("---")
            
            self.log_yaz("Bağlantı kesildi, güvenli duruma geçiliyor.", seviye="hata", mesaj_kutusu_goster=True)
        
            self.btnManuelMod.setEnabled(False)
            self.btnOtomatikMod.setEnabled(False)
            self.lblSistemBaglantisi.setText("● Sistem Bağlı Değil  ")
            self.lblSistemBaglantisi.setStyleSheet("color: #dc2626; border: none; font-size: 14px;")
            self.lblBaglantiDurum.setText("● Bağlantı: Bağlı Değil")
            self.lblBaglantiDurum.setStyleSheet("color: #dc2626;")
         
    def sure_guncelle(self):
        if not self.sayac_calisiyor:
            return

        self.lblStabilizasyon.setStyleSheet("color: green; font-size: 13px;")
        self.gecen_sure_saniye += 1
        dakika = self.gecen_sure_saniye // 60
        saniye = self.gecen_sure_saniye % 60
        metin = f"Stabilizasyon: AKTİF {dakika:02d}:{saniye:02d} / 05:00"

        if self.gecen_sure_saniye > 300:
            self.lblStabilizasyon.setText(metin)
            self.lblStabilizasyon.setStyleSheet("color: #dc2626; font-size: 13px;")
        else:
            self.lblStabilizasyon.setText(metin)
            self.lblStabilizasyon.setStyleSheet("color: green; font-size: 13px;")

    def sayaci_baslat(self):
        self.sayac_calisiyor = True
    def sayaci_durdur(self):
        self.sayac_calisiyor = False

    def hesapla_tiklandi(self):
    
        enlem = self.dsboxEnlem.value()
        boylam = self.dsboxBoylam.value()
        secilen_uydu = self.cboxUyduSecimi.currentText()
        yukseklik = self.dsboxYukseklik.value()#bunu hesaba katmıyoruz arayüzden silelim mi sor.
    
        uydu_boylami = UYDU_BOYLAMLARI[secilen_uydu]

        try:
            az, el = hesapla_azimut_elevasyon(enlem,boylam,uydu_boylami)
        except Exception as hata:
            QMessageBox.warning(self, "Hesaplama Hatası", str(hata))
            return
        
        self.son_hesaplanan_azimut = az
        self.son_hesaplanan_elevasyon = el

        self.log_yaz(f"Hesaplandı: Az={az:.2f}, El={el:.2f}")

    def yonlendir_tiklandi(self):
        azimut_degeri = self.dsboxAzimut.value()
        elevasyon_degeri = self.dsboxElevasyon.value()
        self.hedefe_git(azimut_degeri, elevasyon_degeri)

    def uyduya_yonlendir_tiklandi(self):  
        self.hesapla_tiklandi()    
        azimut_deger = self.son_hesaplanan_azimut
        elevasyon_deger = self.son_hesaplanan_elevasyon
        self.hedefe_git(azimut_deger, elevasyon_deger)

    def hedefe_git(self, azimut_degeri, elevasyon_degeri):
        if self.su_anki_mod != "manuel":
            QMessageBox.warning(self,"Mod Hatası", "Önce Manuel Mod'a geçmelisiniz!")
            return
        
        komut = {"komut": "git", "azimut": azimut_degeri, "elevasyon": elevasyon_degeri} #stm32 kodlayan kişiyle düzenlemelisin 

        self.haberlesme.veri_gonder(komut)
        self.log_yaz(f"Manuel komut gönderildi: Az={azimut_degeri}, El={elevasyon_degeri}")
    

    def durdur_tiklandi(self):

        komut = {"komut": "dur"}

        self.haberlesme.veri_gonder(komut)
        self.log_yaz("DURDUR komutu gönderildi! ")

    def manuel_mod_tiklandi(self):
        self.su_anki_mod = "manuel"

        komut = {"komut": "mod_degistir", "mod": "manuel"} #stm32 kodlayanla konuşulacak
        self.haberlesme.veri_gonder(komut)

        self.lblStabilizasyon.setStyleSheet("color: #cccccc;font-size: 13px;")

        self.gbUyduHesaplama.setEnabled(True)
        self.buton_aktif_yap(self.btnUyduyaYonlendir)

        self.dsboxAzimut.setEnabled(True)
        self.labelAzimutManuel.setEnabled(True)
        self.dsboxElevasyon.setEnabled(True)
        self.labelElevasyonManuel.setEnabled(True)
        self.btnYonlendir.setEnabled(True)
        self.buton_aktif_yap(self.btnYonlendir)

        self.sayaci_durdur()

        self.btnManuelMod.setStyleSheet("background-color: #2563eb; color: white; border-radius: 10px; border: none; padding: 8px 15px; font-size: 13px;")
        self.btnOtomatikMod.setStyleSheet("background-color: white; color: black; border-radius: 10px; border: 1px solid #cccccc; padding: 8px 15px; font-size: 13px; ")

        self.log_yaz("Manuel Mod'a geçildi.")
    
    def otomatik_mod_tiklandi(self):
        self.su_anki_mod = "otomatik"

        komut = {"komut": "mod_degistir", "mod": "otomatik"} #stm32 kodlayanla konuşulacak
        self.haberlesme.veri_gonder(komut)

        self.gbUyduHesaplama.setEnabled(False)
        self.buton_pasif_yap(self.btnUyduyaYonlendir)

        self.dsboxAzimut.setEnabled(False)
        self.labelAzimutManuel.setEnabled(False)
        self.dsboxElevasyon.setEnabled(False)
        self.labelElevasyonManuel.setEnabled(False)
        self.buton_pasif_yap(self.btnYonlendir)
    
        self.sayaci_baslat()

        self.btnOtomatikMod.setStyleSheet("background-color: #2563eb; color: white; border-radius: 10px; border: none; padding: 8px 15px; font-size: 13px;")
        self.btnManuelMod.setStyleSheet("background-color: white; color: black; border-radius: 10px; border: 1px solid #cccccc; padding: 8px 15px; font-size: 13px;")

        self.log_yaz("Otomatik Mod'a geçildi.")

    def buton_aktif_yap(self, buton):
        buton.setEnabled(True)
        buton.setGraphicsEffect(None)

    def buton_pasif_yap(self, buton):
        buton.setEnabled(False)
        efekt = QGraphicsOpacityEffect()
        efekt.setOpacity(0.4)
        buton.setGraphicsEffect(efekt)

    def oku_tiklandi(self):
        komut = {"komut": "pid_oku"} #stm32 kodlayanla konusulmalı.
        self.haberlesme.veri_gonder(komut)

        #hata çıkarsa yine iyileştirme yapılabilir.
        cevap = None
        for deneme in range(10):
            cevap = self.haberlesme.veri_oku()
            if cevap is not None:
                break
            time.sleep(0.1)

        if cevap is None:
            self.log_yaz("PID değerleri okunamadı, cevap gelmedi.", seviye="uyarı")
            return
        
        self.tablePID.setItem(0, 0, QTableWidgetItem(str(cevap.get("azimut_p",0)))) #stm32 kodlayandan alınacak isimler.
        self.tablePID.setItem(0, 1, QTableWidgetItem(str(cevap.get("azimut_i",0))))
        self.tablePID.setItem(0, 2, QTableWidgetItem(str(cevap.get("azimut_d",0))))

        self.tablePID.setItem(1, 0, QTableWidgetItem(str(cevap.get("elevasyon_p",0))))
        self.tablePID.setItem(1, 1, QTableWidgetItem(str(cevap.get("elevasyon_i",0))))
        self.tablePID.setItem(1, 2, QTableWidgetItem(str(cevap.get("elevasyon_d",0))))

        self.log_yaz("PID değerleri okundu ve tabloya yazıldı.")

    def pid_gonder(self, kalici):
        try:
            az_p = float(self.tablePID.item(0, 0).text())
            az_i = float(self.tablePID.item(0, 1).text())
            az_d = float(self.tablePID.item(0, 2).text())
    
            el_p = float(self.tablePID.item(1, 0).text())
            el_i = float(self.tablePID.item(1, 1).text())
            el_d = float(self.tablePID.item(1, 2).text())

        except Exception as hata:
            self.log_yaz("Hatalı giriş yaptınız! ({hata})", seviye="uyarı", mesaj_kutusu_goster=True)
            return
    
        komut = { #stm32 yazanla konuşulmalı
            "komut": "pid_uygula",
            "kalici": kalici,
            "azimut": {"p": az_p, "i": az_i, "d": az_d},
            "elevasyon": {"p": el_p, "i": el_i, "d": el_d}
        }
        self.haberlesme.veri_gonder(komut)
    
        if kalici:
            self.log_yaz("PID değerleri kalıcı olarak kaydedildi (EEPROM/Flash).")
        else:
            self.log_yaz("PID değerleri anlık olarak uygulandı (kalıcı değil).")

    def uygula_tiklandi(self):
        self.pid_gonder(kalici=False)
        
    def kaydet_tiklandi(self):
        self.pid_gonder(kalici=True)

    def log_yaz(self, mesaj, seviye="bilgi", mesaj_kutusu_goster=False):
        saat = datetime.now().strftime("%H:%M:%S")

        if seviye == "hata":
            renk = "#dc2626"
        elif seviye == "uyarı":
            renk = "orange"

        else:
            renk = "black"   

        satir = f"<span style= 'color: {renk};'>[{saat}] {mesaj}</span>"
        self.textEditLog.appendHtml(satir)

        if mesaj_kutusu_goster:
            QMessageBox.warning(self, "Uyarı", mesaj)

        if self.textEditLog.document().blockCount() > 500:
            cursor = self.textEditLog.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        
    def closeEvent(self, event):
        #eğer kapandıktan sonra kaydedilecek daha fazla şey varsa onlarıda bu şekilde yazman gerekiyor.

        self.kamera.release() #görüntü işleme için 

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


