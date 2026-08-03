"""Donanım yokken GUI'nin Wi-Fi yolunu sınamak için ESP32 protokol simülatörü."""

from __future__ import annotations

import json
import math
import socket
import threading
import time

HOST = "0.0.0.0"
PORT = 8080


class SimulatedController:
    def __init__(self) -> None:
        self.azimuth = 163.0
        self.elevation = 42.0
        self.target_azimuth = self.azimuth
        self.target_elevation = self.elevation
        self.mode = "manuel"
        self.stopped = True
        self.sequence = 0
        self.pid = {
            "azimut": {"p": 3.65, "i": 0.58, "d": 0.92},
            "elevasyon": {"p": 3.65, "i": 0.58, "d": 0.92},
        }

    def command(self, request: dict) -> list[dict]:
        command = request.get("komut", "")
        responses = []
        if command == "ping":
            responses.append(self.ack(command, True, "pong"))
        elif command == "git":
            self.target_azimuth = float(request["azimut"])
            self.target_elevation = float(request["elevasyon"])
            self.stopped = False
            responses.append(self.ack(command, True, "Hedef kabul edildi."))
        elif command == "dur":
            self.stopped = True
            self.mode = "manuel"
            responses.append(self.ack(command, True, "Motorlar durduruldu."))
        elif command == "mod_degistir":
            self.mode = str(request.get("mod", "manuel"))
            self.stopped = self.mode == "manuel"
            responses.append(self.ack(command, True, "Mod değiştirildi."))
        elif command == "duzelt":
            self.target_azimuth += float(request.get("delta_azimuth", 0))
            self.target_elevation += float(request.get("delta_elevation", 0))
            responses.append(self.ack(command, True, "Düzeltme uygulandı."))
        elif command == "pid_oku":
            responses.append({"type": "pid", "protocol": 1, "pid": self.pid})
            responses.append(self.ack(command, True, "PID değerleri gönderildi."))
        elif command == "pid_uygula":
            self.pid = {
                "azimut": request["azimut"],
                "elevasyon": request["elevasyon"],
            }
            responses.append(self.ack(command, True, "PID uygulandı."))
        elif command == "sifirla":
            self.azimuth = 0.0
            self.elevation = 0.0
            self.target_azimuth = 0.0
            self.target_elevation = 0.0
            self.stopped = True
            responses.append(self.ack(command, True, "Sanal eksen sıfırı kaydedildi."))
        elif command == "hata_temizle":
            responses.append(self.ack(command, True, "Sanal hata kilidi temizlendi."))
        else:
            responses.append(self.ack(command or "bilinmeyen", False, "Bilinmeyen komut."))
        return responses

    @staticmethod
    def ack(command: str, ok: bool, message: str) -> dict:
        return {
            "type": "ack",
            "protocol": 1,
            "cmd": command,
            "ok": ok,
            "message": message,
        }

    def telemetry(self) -> dict:
        if not self.stopped:
            self.azimuth += max(
                -0.6, min(0.6, self.target_azimuth - self.azimuth)
            )
            self.elevation += max(
                -0.4, min(0.4, self.target_elevation - self.elevation)
            )
        error = math.hypot(
            self.target_azimuth - self.azimuth,
            self.target_elevation - self.elevation,
        )
        self.sequence += 1
        return {
            "type": "telemetry",
            "protocol": 1,
            "seq": self.sequence,
            "mode": self.mode,
            "state": "stopped" if self.stopped else "moving",
            "azimut": round(self.azimuth, 3),
            "elevasyon": round(self.elevation, 3),
            "target_azimut": round(self.target_azimuth, 3),
            "target_elevasyon": round(self.target_elevation, 3),
            "roll": 0.25 * math.sin(time.monotonic()),
            "pitch": 0.25 * math.cos(time.monotonic()),
            "yaw": 0.0,
            "hata_acisi": round(error, 3),
            "hedefe_ulasildi": error <= 0.5,
            "imu_ok": True,
            "encoder_az_ok": True,
            "encoder_el_ok": True,
            "motors_enabled": not self.stopped,
            "laser_on": self.mode == "otomatik",
            "fault": "",
            "calib": {"sys": 3, "gyro": 3, "accel": 3, "mag": 3},
        }


def send_json(connection: socket.socket, message: dict) -> None:
    connection.sendall(
        (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
    )


def serve_client(connection: socket.socket, address) -> None:
    print(f"Arayüz bağlandı: {address[0]}:{address[1]}")
    controller = SimulatedController()
    connection.settimeout(0.05)
    buffer = bytearray()
    next_telemetry = time.monotonic()
    try:
        while True:
            try:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer.extend(chunk)
                while b"\n" in buffer:
                    line, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    if not line.strip():
                        continue
                    request = json.loads(line.decode("utf-8"))
                    for response in controller.command(request):
                        send_json(connection, response)
            except socket.timeout:
                pass
            if time.monotonic() >= next_telemetry:
                send_json(connection, controller.telemetry())
                next_telemetry += 0.1
    except (ConnectionError, OSError, json.JSONDecodeError):
        pass
    finally:
        connection.close()
        print("Arayüz bağlantısı kapandı.")


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(4)
        print(f"Sahte ESP32-S3 sunucusu {HOST}:{PORT} üzerinde hazır.")
        while True:
            connection, address = server.accept()
            threading.Thread(
                target=serve_client, args=(connection, address), daemon=True
            ).start()


if __name__ == "__main__":
    main()
