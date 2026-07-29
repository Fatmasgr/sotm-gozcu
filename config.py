"""
Sistem genelinde kullanılan sabitler ve konfigürasyon değerleri.
Buradaki değerleri değiştirerek kamera/lazer/kalibrasyon ayarlarını
kod içinde başka yere dokunmadan güncelleyebilirsin.
"""

# ---- Kamera / Görüntü ----
FRAME_WIDTH = 800
FRAME_HEIGHT = 600
CAMERA_INDEX = 0

# ---- HSV Kırmızı Lazer Renk Aralıkları (mevcut kod ile birebir aynı) ----
LOWER_RED_1 = (0, 120, 200)
UPPER_RED_1 = (10, 255, 255)
LOWER_RED_2 = (170, 120, 200)
UPPER_RED_2 = (180, 255, 255)

# Gürültü filtresi için minimum kontur alanı
MIN_CONTOUR_AREA = 5

# ---- Kalibrasyon (mevcut kod ile birebir aynı mantık) ----
OUTER_RADIUS_CM = 50
MAX_RADIUS_PIXELS = 250  # bu piksel mesafesi OUTER_RADIUS_CM'e karşılık gelir

# ---- Skor Eşikleri (cm cinsinden, mevcut kod ile birebir aynı) ----
# (üst_sinir_cm, skor) şeklinde sıralı liste
SCORE_THRESHOLDS = [
    (5, 10),
    (10, 9),
    (15, 8),
    (20, 7),
    (25, 6),
]
DEFAULT_SCORE = 5  # yukarıdaki hiçbir aralığa girmezse

# ---- Hedef Kilitlenme Eşiği ----
# Lazer, hedefe bu mesafeden (cm) daha yakınsa target_locked = True kabul edilir.
TARGET_LOCK_THRESHOLD_CM = 5.0

# ---- Kalman Filtresi (yumuşatma / kayıp anında tahmin) ----
KALMAN_PROCESS_NOISE = 0.025
KALMAN_MEASUREMENT_NOISE = 0.45
# Lazer kaybolduğunda kaç kareye kadar tahmin ile devam edilecek
PREDICT_AFTER_LOST_FRAMES = 12

# ---- Lazer İzi (Trail) ----
# İzde tutulacak maksimum nokta sayısı
TRAIL_LENGTH = 70

# ---- Çıkış Tuşu ----
EXIT_KEY = 27  # ESC
