"""
Arayüz / ana işlemci / pan-tilt entegrasyonu için kullanılacak
düzenli veri yapısı.

error_x ve error_y alanları özellikle korunur; ileride motorların
hangi yöne hareket edeceğini belirlemek için doğrudan kullanılacaktır:
- error_x > 0  -> lazer, hedefin sağında
- error_x < 0  -> lazer, hedefin solunda
- error_y > 0  -> lazer, hedefin altında
- error_y < 0  -> lazer, hedefin üstünde
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TargetingData:
    laser_detected: bool
    laser_x: Optional[int]
    laser_y: Optional[int]
    target_x: int
    target_y: int
    error_x: Optional[int]
    error_y: Optional[int]
    pixel_distance: Optional[float]
    cm_distance: Optional[float]
    score: Optional[int]
    target_locked: bool
    # Ek alan: laser_x/laser_y gerçek ölçüm değil, Kalman tahmini ise True.
    # laser_detected=False iken de (kısa süreli kayıpta) koordinat üretmeye
    # devam edebilmek için eklenmiştir; pan-tilt akışının kopmadan
    # sürmesini sağlar. Mevcut zorunlu alanları etkilemez.
    laser_predicted: bool = False

    def to_dict(self) -> dict:
        """Arayüze / API'ye JSON olarak gönderilebilecek sözlük çıktısı."""
        return asdict(self)

    @classmethod
    def no_laser(cls, target_x: int, target_y: int) -> "TargetingData":
        """Lazer bulunamadığında kullanılacak boş/varsayılan veri paketi."""
        return cls(
            laser_detected=False,
            laser_x=None,
            laser_y=None,
            target_x=target_x,
            target_y=target_y,
            error_x=None,
            error_y=None,
            pixel_distance=None,
            cm_distance=None,
            score=None,
            target_locked=False,
        )

    def to_console_report(self) -> str:
        """
        İnsan-okur formatında rapor (arayüzcü arkadaşınla paylaştığın
        örnek çıktı formatı ile birebir aynı, artık tahmin durumu da dahil).
        """
        # Ne gerçek ölçüm ne de tahmin varsa (lazer tamamen kayıp)
        if self.laser_x is None:
            return (
                "Lazer bulundu: HAYIR\n"
                f"Hedef X: {self.target_x}\n"
                f"Hedef Y: {self.target_y}\n"
                "Hedef kilitlendi: HAYIR"
            )

        laser_line = "EVET" if self.laser_detected else "HAYIR (tahmin ediliyor)"

        return (
            f"Lazer bulundu: {laser_line}\n"
            f"Lazer X: {self.laser_x}\n"
            f"Lazer Y: {self.laser_y}\n"
            f"Hedef X: {self.target_x}\n"
            f"Hedef Y: {self.target_y}\n"
            f"X Hatası: {self.error_x} px\n"
            f"Y Hatası: {self.error_y} px\n"
            f"Mesafe: {self.pixel_distance:.2f} px\n"
            f"Mesafe: {self.cm_distance:.2f} cm\n"
            f"Skor: {self.score}\n"
            f"Hedef kilitlendi: {'EVET' if self.target_locked else 'HAYIR'}"
        )
