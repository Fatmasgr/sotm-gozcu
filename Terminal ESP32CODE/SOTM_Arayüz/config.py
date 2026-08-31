"""SOTM-Gözcü arayüzünün kullanıcı tarafından ayarlanabilir sabitleri."""

import os

# ---- Kamera / Görüntü ----
FRAME_WIDTH = 800
FRAME_HEIGHT = 600
# Varsayılan kaynak ESP32-CAM MJPEG akışıdır. USB kamera için ortam
# değişkenini ``SOTM_CAMERA_SOURCE=0`` yapabilirsiniz.
_camera_source = os.getenv(
    "SOTM_CAMERA_SOURCE", "http://sotm-cam.local:81/stream"
)
CAMERA_SOURCE = int(_camera_source) if _camera_source.isdigit() else _camera_source
CAMERA_RECONNECT_SECONDS = 1.0

# OV2640 lensiniz farklıysa saha kalibrasyonuyla güncelleyin.
CAMERA_HORIZONTAL_FOV_DEG = 65.0
CAMERA_VERTICAL_FOV_DEG = 50.0
MAX_CAMERA_CORRECTION_DEG = 1.5
CAMERA_CORRECTION_INTERVAL_FRAMES = 3

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
