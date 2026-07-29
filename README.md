# SOTM-Gözcü Kontrol Paneli 🛰️

**KAPSÜL ATLAS TEKNOFEST 2026 - Hareketli Platformlar İçin Hassas Stabilizasyon ve Lazer Takip Sistemi Arayüz Yazılımı**

**Arayüz Geliştiricisi:** Fatma Sağır

## 📖 Genel Bakış
SOTM-Gözcü arayüzü, Stewart platformu üzerinde hareket eden yer terminalinin yönelimini, stabilizasyonunu ve uydu takip komutlarını tek bir ekrandan yönetmek amacıyla Python ve PyQt5 kullanılarak geliştirilmiştir. Bu sistem, hem manuel kontrol hem de otonom takip yeteneklerini bir araya getirerek, zorlu saha koşullarında kesintisiz iletişim ve takip optimizasyonu sağlamaktadır.

## ✨ Öne Çıkan Özellikler
* **İki Takip Modu:** Manuel Mod'da kullanıcı doğrudan açı değerlerini girerken, Otomatik Mod'da sistem sensör verilerini kullanarak otonom hedef takibi gerçekleştirir.
* **Çift Haberleşme Yolu:** USB (STM32, 115200 baud) ve Wi-Fi (ESP32, TCP soket) destekleri ile tek arayüz üzerinden esnek bağlantı imkanı sunar.
* **Uydu Açı Hesaplama:** GPS koordinatları üzerinden Türksat 4B / 5A uyduları için azimut ve elevasyon değerleri otomatik hesaplanarak doğrudan yönlendirme komutlarına dönüştürülür.
* **Donanımsız Test Altyapısı:** Gömülü sistem kartı hazır olmadan da arayüzün tam kapsamlı test edilmesini sağlayan yerleşik bir simülasyon modu mevcuttur.
* **Kamera Tabanlı İnce Ayar:** HSV + Kalman filtresi entegrasyonu ile tespit edilen lazer konumu, hedef merkezine göre kademeli (cascaded) bir düzeltme sinyaline çevrilir.

## 🎛️ Panel Bazlı İşlev Özeti

| Panel Adı | İşlev ve Kapsam |
| :--- | :--- |
| **Sistem Durumu** | Azimut, elevasyon, roll/pitch/yaw ve hata açısını IMU + enkoder verisinden canlı gösterir. Stabilizasyon süresi sayacı barındırır. |
| **Bağlantı Ayarları** | USB (STM32) veya Wi-Fi (ESP32) seçimi; port/baud rate veya IP adresi tabanlı bağlantı yönetimi sağlar. |
| **Manuel Kontrol** | 0-360° azimut ve 0-90° elevasyon açılarının manuel olarak iletilmesini ve acil durdurma (DURDUR) fonksiyonunu içerir. |
| **Uydu Hesaplama** | Enlem/boylam/yükseklik verileriyle Türksat 4B / 5A azimut-elevasyon hesaplamalarını ve doğrudan yönlendirme otomasyonunu yapar. |
| **Görüntü İşlem** | Kameradan canlı görüntü akışı, HSV ve Kalman filtreleri ile kırmızı lazer noktası tespiti, hedef merkezine uzaklık ölçümü sunar. |
| **Parametreler (PID)** | Azimut ve elevasyon eksenleri için P, I, D değerlerinin okunması, test edilmesi ve kalıcı hafızaya (EEPROM/Flash) kaydedilmesini sağlar. |
| **Sistem Log** | Zaman damgalı ve renk kodlu (bilgi, uyarı, hata) olay kayıtlarını tutar. Bağlantı kesintilerini otomatik raporlar. |

## ⚙️ Teknik Mimari
* **Haberleşme Protokolü:** Tüm komutlar, STM32 tarafıyla paylaşılan ortak bir anahtar sözlüğü ile JSON formatında (örn. `{"komut": "git", "azimuth":.., "elevation": ..}`) aktarılır.
* **Canlı Veri Döngüsü:** 100 milisaniye aralıklarla tetiklenen zamanlayıcı sayesinde sensör verileri sürekli güncellenir.
* **Güvenlik Mekanizması:** 1 saniyeden uzun süren veri kesintilerinde sistem otonom olarak güvenli moda geçer, arayüz butonlarını kilitler ve operatörü uyarır.
* **Kalıcı Hafıza:** Kullanıcının son tercih ettiği port, IP, GPS lokasyonu ve uydu seçimi uygulama kapanışında kaydedilir.
* **Kademeli (Cascaded) Kontrol:** STM32 üzerindeki IMU tabanlı iç döngü platform sarsıntılarını sönümlerken; PC üzerindeki kamera geri beslemesi lazer-hedef hizasındaki hassas hataları telafi eder.

## 🚀 Geliştirme Durumu
- [x] Haberleşme katmanı (USB+Wi-Fi)
- [x] Simülasyon modu (donanımsız test)
- [x] Manuel / Otomatik mod geçişi
- [x] Uydu açı hesaplama (4B/5A)
- [x] PID okuma / uygulama / kaydetme
- [x] Sistem log ve uyarı mekanizması
- [x] Ayarların kalıcı hafızası & Bağlantı güvenliği
- [x] Kamera + lazer tespit entegrasyonu
- [ ] Kademeli kontrol (Kamera -> STM32 entegrasyonu) *(Protokol Netleşiyor)*
- [ ] Gerçek STM32 ile saha testi *(Bekliyor)*
