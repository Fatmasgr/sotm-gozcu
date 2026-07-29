import socket

sunucu = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sunucu.bind(("0.0.0.0",8080))
sunucu.listen(1)
print("Sahte ESP32 sunucu bekliyor...")

baglanti, adres = sunucu.accept()
print("Bir istemci bağlandı: ", adres)

while True:
    veri = baglanti.recv(1024)
    if veri:
        print("Gelen veri: ", veri.decode())