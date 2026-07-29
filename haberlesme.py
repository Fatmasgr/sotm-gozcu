import serial
import json
import random
import socket
import serial.tools.list_ports

class Haberlesme:
    def __init__(self):
        self.baglanti = None
        self.baglanti_tipi = None
        self.son_hata = None

    def baglan_usb(self,port_adi,baud_rate):
        try:
            self.baglanti = serial.Serial(port_adi,baud_rate,timeout=1)
            self.baglanti_tipi = "usb"
            return True
        except Exception as hata:
            print("USB bağlantı Hatası: ", hata)
            return False
        
    def baglan_wifi(self,ip_adresi):
        try:
            WIFI_PORT = 8080 #ESP32 PROGRAMLAYAN KİŞİYE SOR SABİT PORT NUMARASI
            self.baglanti = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.baglanti.settimeout(3)
            self.baglanti.connect((ip_adresi,WIFI_PORT))
            self.baglanti_tipi = "wifi"
            return True

        except Exception as hata:
            print("Wi-Fi bağlantı hatası: ", hata)
            return False

    def baglantiyi_kes(self):
        try:
            if self.baglanti is not None:
                self.baglanti.close()
                self.baglanti = None
            return True
        except Exception as hata:
            print("Bağlantı Kesme Hatası: ",hata)
            return False

    def veri_gonder(self,mesaj):
        try:
            json_metni = json.dumps(mesaj) + "\n"

            if self.baglanti_tipi == "usb":
                self.baglanti.write(json_metni.encode())
            elif self.baglanti_tipi == "wifi":
                self.baglanti.send(json_metni.encode())

            return True   
        except Exception as hata:
            print("Veri Gönderme Hatası: ", hata)
            return False
    
    def veri_oku(self):
        try:

            if self.baglanti_tipi == "usb":
                satir = self.baglanti.readline()
            elif self.baglanti_tipi == "wifi":
                satir = self.baglanti.recv(1024)
            else:
                return None
            
            satir_yazi = satir.decode().strip()

            if satir == "" :
                return None
            
            veri = json.loads(satir_yazi)
            return veri
        except Exception as hata:
            print("Veri Okuma Hatası: ", hata)
            return None
        
class SahteHaberlesme:
    def __init__(self):
        self.azimut_deger = 163.0
        self.elevasyon_deger = 42.0

    def baglan(self,port_adi,baud_rate):
        #print("Sahte Bağlantı Kuruldu (Gerçek kart yok)")
        return True
    
    def baglantiyi_kes(self):
        #print("Bağlantı kesildi!")
        return True
    
    def veri_gonder(self,mesaj):
        #print("Veri gönderildi: ",mesaj)
        return True

    def veri_oku(self):
        self.azimut_deger = self.azimut_deger + random.uniform(-0.8,0.8)
        self.elevasyon_deger = self.elevasyon_deger + random.uniform(-0.5,0.5)

        return { "Azimut: ": round(self.azimut_deger,2),
                "Elevasyon: ": round(self.elevasyon_deger,2),
                "roll ": round(random.uniform(-180,180),2),
                "pitch ": round(random.uniform(-90,90),2),
                "yaw ": round(random.uniform(-180,180),2),
                "azimut_p": 1.5,
                "azimut_i": 0.3,
                "azimut_d": 0.05,
                "elevasyon_p": 1.2,
                "elevasyon_i": 0.25,
                "elevasyon_d": 0.04
            }

def portlari_listele ():

    portlar = serial.tools.list_ports.comports()
    port_isimleri = []
    for p in portlar:
        port_isimleri.append(p.device)
    return port_isimleri


        
