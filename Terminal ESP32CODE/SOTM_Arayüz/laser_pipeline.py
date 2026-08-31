"""
Lazer-Hedef Görüntü İşleme Sistemi - Ana çalıştırma noktası.

Akış:
  Kamera -> HSV Lazer Tespiti -> Kalman ile yumuşatma/tahmin
  -> Hedef Merkezi Karşılaştırması -> TargetingData üretimi
  -> İz (trail) kaydı -> Görsel Overlay -> (arayüze) veri çıktısı

Bu modül, görüntü işleme -> Python arayüzü -> ESP32-S3 pan/tilt kontrol
zincirinde kullanılan `TargetingData` nesnesini üretir. Motor komutunun
gönderilmesi `main.py`, gerçek zamanlı motor kontrolü ise ESP32-S3 firmware'i
tarafından yapılır.

Tuşlar:
  ESC : Çıkış
  R   : Lazer izini sıfırla (aynı işi dışarıdan `reset_trail()` ile de yapabilirsin)
"""

import cv2

import config
from laser_detector import LaserDetector
from laser_tracker import LaserTracker
from targeting import build_targeting_data
from trail import LaserTrail
from visualizer import draw_targeting_overlay, draw_trail


def on_targeting_data(data):
    """
    Üretilen TargetingData ile ne yapılacağını belirleyen callback.

    Şu an için konsola arayüz-dostu rapor basıyor. İleride bu fonksiyon
    yerine data.to_dict() çıktısını doğrudan arayüze / API'ye / pan-tilt
    kontrol modülüne gönderebilirsin.
    """
    print(data.to_console_report())
    print("-" * 40)


class LaserTargetSystem:
    """
    Sistemin tüm durumunu (dedektör, tracker, iz) bir arada tutan sınıf.
    Dışarıdan (arayüz/ana işlemci) bir örneğini elinde tutup örn.
    `system.reset_trail()` çağırarak izi istediğin an sıfırlayabilirsin.
    """

    def __init__(self):
        self.detector = LaserDetector()
        self.tracker = LaserTracker()
        self.trail = LaserTrail()
        self.lost_frames = 0

    def reset_trail(self) -> None:
        """İzi temizler. Kamera döngüsünü durdurmadan çağrılabilir."""
        self.trail.reset()

    def reset_tracking(self) -> None:
        """İz + Kalman filtresi durumunu tamamen sıfırlar."""
        self.trail.reset()
        self.tracker.reset()
        self.lost_frames = 0

    def process_frame(self, frame):
        """
        Tek bir kareyi işler: tespit + yumuşatma/tahmin + hedefle
        karşılaştırma + iz güncelleme + çizim.

        Returns: (islenmis_frame, targeting_data)
        """
        frame_height, frame_width = frame.shape[:2]

        raw = self.detector.detect(frame)

        if raw.detected:
            laser_x, laser_y = self.tracker.update(raw.x, raw.y, frame_width, frame_height)
            laser_detected = True
            laser_predicted = False
            self.lost_frames = 0
        else:
            self.lost_frames += 1
            predicted = self.tracker.predict(frame_width, frame_height)
            if predicted is not None and self.lost_frames <= config.PREDICT_AFTER_LOST_FRAMES:
                laser_x, laser_y = predicted
                laser_detected = False
                laser_predicted = True
            else:
                # Lazer uzun süredir kayıp: tahmin de güvenilir değil
                self.tracker.reset()
                laser_x, laser_y = None, None
                laser_detected = False
                laser_predicted = False

        targeting_data = build_targeting_data(
            laser_detected, laser_predicted, laser_x, laser_y, frame_width, frame_height
        )

        # İz güncelleme: koordinat varsa ekle, hiç yoksa kopukluk için None ekle
        if laser_x is not None and laser_y is not None:
            self.trail.add((laser_x, laser_y))
        else:
            self.trail.add(None)

        frame = draw_trail(frame, self.trail.get_points())
        frame = draw_targeting_overlay(frame, targeting_data)

        return frame, targeting_data


def run():
    cap = cv2.VideoCapture(config.CAMERA_SOURCE)
    system = LaserTargetSystem()

    if not cap.isOpened():
        print("Kamera açılamadı.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

            frame, targeting_data = system.process_frame(frame)

            # Arayüz entegrasyonu için veri paketi burada üretiliyor:
            # targeting_data.to_dict()
            on_targeting_data(targeting_data)

            cv2.imshow("Laser Target System", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == config.EXIT_KEY:
                break
            if key in (ord("r"), ord("R")):
                system.reset_trail()
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
