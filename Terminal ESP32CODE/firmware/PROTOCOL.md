# SOTM-Gözcü JSON Protokolü

Taşıma katmanı USB seri (`115200 8N1`) veya TCP (`8080`) olabilir. Her paket
UTF-8 kodlu, tek satırlık bir JSON nesnesidir ve `\n` ile biter. TCP paket
sınırları mesaj sınırı değildir; alıcı satır sonuna kadar tamponlamalıdır.

## Komutlar

```json
{"komut":"ping"}
{"komut":"git","azimut":163.2,"elevasyon":42.0}
{"komut":"dur"}
{"komut":"mod_degistir","mod":"manuel"}
{"komut":"mod_degistir","mod":"otomatik"}
{"komut":"duzelt","delta_azimuth":-0.12,"delta_elevation":0.08}
{"komut":"pid_oku"}
{"komut":"pid_uygula","kalici":true,"azimut":{"p":3.65,"i":0.58,"d":0.92},"elevasyon":{"p":3.65,"i":0.58,"d":0.92}}
{"komut":"sifirla"}
{"komut":"hata_temizle"}
```

Her komut `ack` ile onaylanır:

```json
{"type":"ack","protocol":1,"cmd":"git","ok":true,"message":"Hedef kabul edildi."}
```

`pid_oku`, ayrıca `type=pid` yanıtı üretir.

## Telemetri

Kontrolcü 10 Hz hızında aşağıdaki alanları yayınlar:

```json
{
  "type":"telemetry",
  "protocol":1,
  "seq":42,
  "uptime_ms":123456,
  "mode":"otomatik",
  "state":"tracking",
  "azimut":163.0,
  "elevasyon":42.0,
  "target_azimut":163.1,
  "target_elevasyon":41.9,
  "roll":0.2,
  "pitch":-0.4,
  "yaw":181.0,
  "hata_acisi":0.17,
  "hedefe_ulasildi":true,
  "imu_ok":true,
  "encoder_az_ok":true,
  "encoder_el_ok":true,
  "motors_enabled":true,
  "laser_on":true,
  "fault":"",
  "calib":{"sys":3,"gyro":3,"accel":3,"mag":3}
}
```

`fault` boş değilse motorlar ve lazer donanımsal olarak güvenli duruma alınır.
`hata_temizle` ancak normalde kapalı acil dur zinciri tekrar güvenli olduğunda
kilidi kaldırır.
