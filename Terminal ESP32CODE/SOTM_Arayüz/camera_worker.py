"""ESP32-CAM/USB kamera okuma ve lazer işleme işini GUI iş parçacığından ayırır."""

from __future__ import annotations

import platform
import time

import cv2
from PyQt5.QtCore import QThread, pyqtSignal

import config
from laser_pipeline import LaserTargetSystem


class CameraWorker(QThread):
    frame_ready = pyqtSignal(object, object)
    status_changed = pyqtSignal(str)

    def __init__(self, source=config.CAMERA_SOURCE, parent=None):
        super().__init__(parent)
        self.source = source
        self._running = True
        self._system = LaserTargetSystem()

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def reset_tracking(self) -> None:
        self._system.reset_tracking()

    def run(self) -> None:
        while self._running and not self.isInterruptionRequested():
            capture = cv2.VideoCapture()
            if isinstance(self.source, str):
                if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                    capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)
                if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                    capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 1500)
                capture.open(self.source)
            elif platform.system() == "Windows":
                capture.open(self.source, cv2.CAP_MSMF)
            else:
                capture.open(self.source)
            if not capture.isOpened():
                self.status_changed.emit("Kamera bağlantısı bekleniyor")
                capture.release()
                time.sleep(config.CAMERA_RECONNECT_SECONDS)
                continue

            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.status_changed.emit("Kamera bağlı")
            while self._running and not self.isInterruptionRequested():
                ok, frame = capture.read()
                if not ok:
                    self.status_changed.emit("Kamera akışı kesildi; yeniden bağlanıyor")
                    break
                frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
                processed, data = self._system.process_frame(frame)
                self.frame_ready.emit(processed, data)
            capture.release()

        self.status_changed.emit("Kamera durduruldu")
