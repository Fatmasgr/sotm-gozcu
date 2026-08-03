from __future__ import annotations

import json
import socket
import threading
import time

from haberlesme import Haberlesme


def _sunucu(port_holder: list[int], ready: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port_holder.append(server.getsockname()[1])
    ready.set()
    connection, _ = server.accept()
    connection.settimeout(2)
    command = b""
    while b"\n" not in command:
        command += connection.recv(128)
    assert json.loads(command.decode("utf-8"))["komut"] == "ping"

    first = b'{"type":"tele'
    second = (
        b'metry","azimut":12.5,"elevasyon":30.0}\n'
        b'{"type":"ack","cmd":"ping","ok":true}\n'
    )
    connection.sendall(first)
    time.sleep(0.03)
    connection.sendall(second)
    time.sleep(0.1)
    connection.close()
    server.close()


def test_tcp_parcali_ve_birlesik_json_paketleri() -> None:
    ready = threading.Event()
    port_holder: list[int] = []
    thread = threading.Thread(
        target=_sunucu, args=(port_holder, ready), daemon=True
    )
    thread.start()
    assert ready.wait(2)

    haberlesme = Haberlesme()
    assert haberlesme.baglan_wifi("127.0.0.1", port_holder[0])
    assert haberlesme.veri_gonder({"komut": "ping"})

    messages = []
    deadline = time.monotonic() + 2
    while len(messages) < 2 and time.monotonic() < deadline:
        message = haberlesme.veri_oku()
        if message is not None:
            messages.append(message)
        time.sleep(0.01)
    haberlesme.baglantiyi_kes()
    thread.join(timeout=1)

    assert [message["type"] for message in messages] == ["telemetry", "ack"]
    assert messages[0]["azimut"] == 12.5


def test_baglanti_yokken_gonderim_reddedilir() -> None:
    haberlesme = Haberlesme()
    assert not haberlesme.veri_gonder({"komut": "dur"})
    assert haberlesme.son_hata == "Aktif bağlantı yok."

