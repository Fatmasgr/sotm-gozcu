from haberlesme import SahteHaberlesme
h = SahteHaberlesme()

# Bağlantı Oluşturma
port_adi = input("Port Adını Giriniz: ")
sonuc = h.baglan(port_adi,9600)
if sonuc:
    print("Bağlantı Başarılı!")
else:
    print("Bağlantı başarısız, port ismini kontrol ediniz.")

# Veri gönderme 
if sonuc:
    mesaj = input("Gönderilecek mesajı yazınız. ")
    veri = h.veri_gonder(mesaj)
    if veri:
        print("Veri Gönderildi!")
    else:
        print("Veri Gönderilemedi!")
else:
    print("Bağlantı başarısız, port ismini kontrol ediniz.")

# Veri Okuma
if sonuc:
    for i in range(5):
        gelen_veri = h.veri_oku()
        print("Gelen veri: ",gelen_veri)
else:
    print("Bağlantı başarısız, port ismini kontrol ediniz.")

# Bağlantı Kesme
if sonuc:
    h.baglantiyi_kes()
    print("Bağlantı kesildi!")
else:
    print("Bağlantı başarısız, port ismini kontrol ediniz.")
