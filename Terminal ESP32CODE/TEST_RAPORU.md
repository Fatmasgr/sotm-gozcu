# SOTM-Gözcü Yazılım Test Raporu

**Tarih:** 31 Temmuz 2026  
**Kapsam:** ESP32-S3 kontrolcü, klasik ESP32 Wi-Fi köprüsü, ESP32-CAM,
Python/PyQt5 arayüzü ve aralarındaki JSON protokolü

## Sonuç özeti

| Test alanı | Sonuç |
|---|---|
| Python 3.12.13 bağımlılık denetimi | Başarılı |
| Tüm Python modüllerinin içe aktarılması | Başarılı |
| Python sözdizimi/bytecode derlemesi | Başarılı |
| Qt Designer UI XML doğrulaması | Başarılı |
| Python birim ve entegrasyon testleri | **26/26 başarılı** |
| OpenCV yapay kırmızı lazer algılama | Başarılı |
| Kalman kısa kayıp tahmini ve uzun kayıp sıfırlaması | Başarılı |
| Sahte ESP32 ile GUI uçtan uca testi | Başarılı |
| Gerçek kamera olmadan GUI açılış/kapanış testi | Başarılı |
| ESP32-S3 temiz firmware derlemesi | Başarılı |
| Klasik ESP32 köprü temiz firmware derlemesi | Başarılı |
| ESP32-CAM temiz firmware derlemesi | Başarılı |

## Temiz firmware derleme değerleri

Derlemeden önce üç hedefin `.pio/build` çıktıları PlatformIO `clean` hedefiyle
silinmiş, ardından tüm kaynaklar yeniden derlenmiştir.

| Hedef | RAM | Flash |
|---|---:|---:|
| ESP32-S3 kontrolcü | 24.928 / 327.680 bayt (%7,6) | 352.901 / 6.553.600 bayt (%5,4) |
| Klasik ESP32 köprü | 44.736 / 327.680 bayt (%13,7) | 747.277 / 1.310.720 bayt (%57,0) |
| ESP32-CAM | 57.956 / 327.680 bayt (%17,7) | 879.549 / 3.145.728 bayt (%28,0) |

Oluşturulan firmware binary dosyaları:

| Hedef | Binary boyutu | SHA-256 |
|---|---:|---|
| ESP32-S3 kontrolcü | 353.264 bayt | `4ECD14DADAA963BBF7D897C75A44ABF089562BF0BE012B87AF6B795E6C6048F6` |
| Klasik ESP32 köprü | 753.856 bayt | `15053ACAE62F7FB3ED759D3ED0FEAF02F3AD9E09AAA2CCA7E028A59951F08CB8` |
| ESP32-CAM | 886.128 bayt | `613B056B97B4875009D5C304B9FE45744B0C8910329C34F41541709B2B398F1B` |

## Doğrulanan yazılım davranışları

- Parçalanmış ve birleştirilmiş TCP JSON paketlerinin doğru tamponlanması
- Bağlantı yokken komutun güvenli biçimde reddedilmesi
- Türksat 4B bakış açısı ve koordinat sınır kontrolleri
- Piksel hatasının kamera görüş açısına çevrilip sınırlandırılması
- Otomatik mod reddedildiğinde GUI'nin manuel moda dönmesi
- Durdur onayından sonra GUI'nin manuel moda dönmesi
- Kırmızı lazer noktasının HSV/OpenCV ile bulunması
- Hedef merkezinde kilit ve skor hesabı
- Kısa lazer kaybında Kalman tahmini
- Uzun lazer kaybında tahmin ve iz durumunun temizlenmesi
- Ping, hedef, mod, düzeltme, PID, sıfır, hata temizleme ve durdurma
  komutlarının ACK üretmesi
- Sahte kontrolcünün hedefe kademeli olarak yaklaşması
- GUI'nin TCP ile bağlanması, telemetriyi göstermesi, hedef göndermesi,
  otomatik moda geçmesi, PID okuması ve durması

## Test sırasında düzeltilen noktalar

- PID okuma komutuna protokolün gerektirdiği ACK yanıtı eklendi.
- Sahte ESP32 sunucusuna `sifirla` ve `hata_temizle` davranışları eklendi.
- Kamera işlem hattının artık GUI ve ESP32-S3 motor kontrolüne bağlı olduğunu
  açıklayan eski modül metni güncellendi.
- OpenCV lazer algılama ve Kalman kayıp davranışı için yeni testler eklendi.
- Tek komutla tekrar çalıştırılabilen `smoke_test_e2e.py` oluşturuldu.

## Donanım üzerinde henüz doğrulanamayanlar

Bilgisayarda hedef ESP32 kartlarına ait bir seri port bulunmadığı için firmware
yükleme ve gerçek sensör/motor testi yapılmamıştır. Aşağıdaki maddeler fiziksel
donanım bağlandığında zorunlu olarak uygulanmalıdır:

1. Üç firmware'in doğru kartlara yüklenmesi ve açılış mesajlarının okunması.
2. NC acil dur girişinin açılmasıyla motor/lazer çıkışlarının ölçülerek kesilmesi.
3. Her AS5600 mıknatıs ve yön işaretinin ayrı ayrı doğrulanması.
4. BNO055 roll, pitch ve yaw eksen/yönlerinin mekanik hareketle doğrulanması.
5. Motor gücü kapalıyken STEP/DIR/ENABLE sinyallerinin osiloskopla ölçülmesi.
6. Düşük akım ve 2–5° hedefle motor yönü, dişli oranı ve enkoder geri beslemesi.
7. Elevasyon 0°/90° mekanik limit ve azimut slip-ring testi.
8. ESP32-CAM gerçek görüntüsünde lazer HSV/FOV saha kalibrasyonu.
9. ±8° hareket, 10 saniye periyot, 8 saniye yeniden yönelim ve 5 dakika takip
   kabul testleri.

Bu fiziksel testler yapılmadan sistemin mekanik olarak yarışmaya hazır olduğu
iddia edilmemelidir; mevcut rapor yazılım ve donanımsız entegrasyon katmanının
başarılı olduğunu doğrular.
