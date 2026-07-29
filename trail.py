"""
Lazerin son N konumunu tutan basit iz (trail) yapısı.

Dışarıdan (arayüz/ana işlemci) `reset()` çağrılarak iz her an
sıfırlanabilir. `None` eklenmesi, iz üzerinde bir "kopukluk"
(lazer uzun süre kaybolmuş) anlamına gelir; çizim sırasında bu
kopukluklarda çizgi çekilmez.
"""

from collections import deque
from typing import Deque, List, Optional, Tuple

import config

Point = Optional[Tuple[int, int]]


class LaserTrail:
    def __init__(self, max_length: int = config.TRAIL_LENGTH):
        self._points: Deque[Point] = deque(maxlen=max_length)

    def add(self, point: Point) -> None:
        """Yeni bir nokta (veya kopukluk için None) ekler."""
        self._points.append(point)

    def reset(self) -> None:
        """İzi tamamen temizler. Arayüzden veya 'r' tuşundan çağrılabilir."""
        self._points.clear()

    def get_points(self) -> List[Point]:
        return list(self._points)

    def __len__(self) -> int:
        return len(self._points)
