# 🔌 TP-Link HS110 Akıllı Priz Kontrol Aracı

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-17%20passed-brightgreen)](tests/)

TP-Link HS110 akıllı prizleri yerel ağ üzerinden TCP/IP ile kontrol etmek için geliştirilmiş, saf Python CLI aracıdır. Harici bağımlılık gerektirmez — sadece Python standart kütüphanesini kullanır.

---

## 📋 İçindekiler

- [✨ Özellikler](#-özellikler)
- [🏗️ Mimari](#️-mimari)
- [📁 Proje Yapısı](#-proje-yapısı)
- [⚙️ Gereksinimler](#️-gereksinimler)
- [🚀 Kurulum](#-kurulum)
- [📖 Kullanım](#-kullanım)
  - [Cihaz Bilgisi](#cihaz-bilgisi)
  - [Enerji Tüketimi](#enerji-tüketimi)
  - [Aç / Kapat](#aç--kapat)
  - [LED Kontrolü](#led-kontrolü)
  - [Canlı İzleme (Polling)](#canlı-i̇zleme-polling)
  - [Ham (Raw) Komut](#ham-raw-komut)
- [🔌 Protokol Detayları](#-protokol-detayları)
- [📊 Veri Modelleri](#-veri-modelleri)
- [🧪 Testler](#-testler)
- [🐍 Programatik Kullanım (API)](#-programatik-kullanım-api)
- [🤝 Katkıda Bulunma](#-katkıda-bulunma)
- [📄 Lisans](#-lisans)

---

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 📟 **Cihaz Bilgisi** | Model, MAC adresi, firmware, sinyal gücü (RSSI), çalışma süresi |
| ⚡ **Enerji İzleme** | Anlık voltaj (V), akım (A), güç (W), toplam tüketim (Wh) |
| 💡 **Güç Kontrolü** | Prizi açma/kapatma |
| 🔦 **LED Kontrolü** | Priz üzerindeki LED göstergesini açma/kapatma |
| 🔄 **Canlı İzleme** | Ayarlanabilir aralıklarla sürekli durum izleme (polling) |
| 📊 **Günlük/Aylık İstatistik** | Günlük ve aylık enerji tüketim istatistikleri |
| ⏱️ **Zamanlayıcı** | Geri sayım zamanlayıcısı ile otomatik açma/kapatma |
| 📡 **WiFi Tarama** | Çevredeki WiFi ağlarını listeleme |
| 🔧 **Ham Komut** | Cihaza doğrudan JSON komutları gönderme |
| 🚫 **Sıfır Bağımlılık** | Yalnızca Python standart kütüphanesi kullanılır |

---

## 🏗️ Mimari

```
┌────────────────────────────────────────────────────────────┐
│                        main.py                             │
│                   (CLI Arayüzü — argparse)                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  device.py   │    │  poller.py   │    │  models.py   │  │
│  │ HS110Device  │◄───│ DevicePoller │    │ DeviceInfo   │  │
│  │ TCP Client   │    │ Thread-based │    │ EnergyInfo   │  │
│  │              │    │ Monitoring   │    │ DeviceStatus │  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘  │
│         │                                                  │
│  ┌──────▼───────┐                                          │
│  │ protocol.py  │                                          │
│  │ XOR Autokey  │                                          │
│  │ Encrypt/     │                                          │
│  │ Decrypt      │                                          │
│  └──────────────┘                                          │
│                                                            │
│         ▼ TCP Port 9999                                    │
│  ┌──────────────┐                                          │
│  │  TP-Link     │                                          │
│  │  HS110       │                                          │
│  └──────────────┘                                          │
└────────────────────────────────────────────────────────────┘
```

---

## 📁 Proje Yapısı

```
Akilli_priz/
├── main.py              # CLI giriş noktası — argparse tabanlı komut satırı arayüzü
├── device.py            # HS110Device sınıfı — cihazla TCP iletişimi
├── models.py            # Veri modelleri (DeviceInfo, EnergyInfo, DeviceStatus)
├── protocol.py          # XOR Autokey şifreleme/çözme protokolü
├── poller.py            # DevicePoller — arka plan thread ile sürekli izleme
├── run_tests.py         # Hızlı test çalıştırıcı (pytest bağımsız)
├── requirements.txt     # Bağımlılıklar (sadece standart kütüphane)
├── .gitignore           # Git dışlama kuralları
└── tests/
    ├── __init__.py
    ├── test_protocol.py # Şifreleme protokolü birim testleri
    └── test_device.py   # Cihaz istemci birim testleri
```

---

## ⚙️ Gereksinimler

- **Python 3.10+** (f-string, type hints, `dataclasses` desteği)
- TP-Link HS110 akıllı priz (aynı yerel ağda)
- Harici paket gerekmez ✅

> **Not:** Testler için opsiyonel olarak `pytest` kullanılabilir, ancak `run_tests.py` hiçbir ek bağımlılık gerektirmez.

---

## 🚀 Kurulum

```bash
# 1. Repoyu klonlayın
git clone https://github.com/CodebyCodef/Akilli_priz.git
cd Akilli_priz

# 2. (Opsiyonel) Sanal ortam oluşturun
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Testleri çalıştırarak kurulumu doğrulayın
python run_tests.py
```

> **İpucu:** Harici bağımlılık olmadığından `pip install` adımı gerekmez.

---

## 📖 Kullanım

### Genel Sözdizimi

```bash
python main.py --ip <CİHAZ_IP> --action <EYLEM> [SEÇENEKLER]
```

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `--ip` | HS110 cihazının IP adresi | *(zorunlu)* |
| `--action` | Yapılacak eylem | *(zorunlu)* |
| `--interval` | Polling aralığı (saniye) | `5.0` |
| `--timeout` | Soket zaman aşımı (saniye) | `2.0` |
| `--command` | Ham JSON komutu (`raw` eylemi için) | — |
| `-v, --verbose` | Debug log çıktısı | `False` |

### Cihaz Bilgisi

```bash
python main.py --ip 192.168.1.100 --action info
```

Örnek çıktı:
```
══════════════════════════════════════════════════
  📟 Device: Oturma Odası Priz
  📋 Model:  HS110(TR)
  🔗 MAC:    AA:BB:CC:DD:EE:FF
  💡 Power:  🟢 ON
  💡 LED:    🟢 ON
  📶 RSSI:   -42 dBm
  ⏱️  Uptime: 86400s
  🔧 SW:     1.5.6 Build 20200318
  🔧 HW:     2.0
══════════════════════════════════════════════════
```

### Enerji Tüketimi

```bash
python main.py --ip 192.168.1.100 --action energy
```

Örnek çıktı:
```
══════════════════════════════════════════════════
  ⚡ Voltage:  220.5 V
  ⚡ Current:  0.450 A
  ⚡ Power:    99.2 W
  ⚡ Total:    12500 Wh
══════════════════════════════════════════════════
```

### Aç / Kapat

```bash
# Prizi aç
python main.py --ip 192.168.1.100 --action on

# Prizi kapat
python main.py --ip 192.168.1.100 --action off
```

### LED Kontrolü

```bash
# LED'i aç
python main.py --ip 192.168.1.100 --action led-on

# LED'i kapat
python main.py --ip 192.168.1.100 --action led-off
```

### Canlı İzleme (Polling)

Belirli aralıklarla cihaz durumunu sürekli izler. `Ctrl+C` ile durdurulur.

```bash
# Varsayılan 5 saniye aralıkla
python main.py --ip 192.168.1.100 --action poll

# 3 saniye aralıkla
python main.py --ip 192.168.1.100 --action poll --interval 3
```

Örnek çıktı:
```
🔄 Polling 192.168.1.100 every 3.0s (Ctrl+C to stop)

[#1] 🟢 Oturma Odası Priz | Power: 98.5W | Voltage: 220.3V | Time: 2026-03-02T13:30:00
[#2] 🟢 Oturma Odası Priz | Power: 99.1W | Voltage: 220.5V | Time: 2026-03-02T13:30:03
[#3] 🟢 Oturma Odası Priz | Power: 97.8W | Voltage: 220.1V | Time: 2026-03-02T13:30:06
^C
⏹️  Stopping poller...
✅ Polling stopped after 3 readings.
```

### Ham (Raw) Komut

Cihaza doğrudan TP-Link Smart Home protokol komutları gönderin:

```bash
python main.py --ip 192.168.1.100 --action raw --command '{"system":{"get_sysinfo":{}}}'
```

---

## 🔌 Protokol Detayları

TP-Link HS110, **TCP port 9999** üzerinde özel bir şifreleme protokolü kullanır:

### XOR Autokey Cipher

| Adım | Açıklama |
|------|----------|
| 1 | JSON komutu string olarak hazırlanır |
| 2 | 4 byte Big Endian uzunluk başlığı eklenir |
| 3 | Her karakter, başlangıç anahtarı `0xAB` ile XOR'lanır |
| 4 | Her adımda anahtar, şifreli byte ile güncellenir (autokey) |

#### Şifreleme (Encrypt)

```
Başlangıç anahtarı: key = 0xAB
Her karakter için:
  encrypted_byte = char XOR key
  key = encrypted_byte
```

#### Çözme (Decrypt)

```
Başlangıç anahtarı: key = 0xAB
İlk 4 byte atlanır (uzunluk başlığı)
Her byte için:
  decrypted = byte XOR key
  key = byte
```

> **Referans:** [TP-Link Smart Home Protocol](https://github.com/softScheck/tplink-smartplug)

---

## 📊 Veri Modelleri

### `DeviceInfo`
Cihaz sistem bilgilerini temsil eder (`get_sysinfo` yanıtı):

| Alan | Tip | Açıklama |
|------|-----|----------|
| `ip` | `str` | Cihaz IP adresi |
| `alias` | `str` | Kullanıcı tanımlı isim |
| `model` | `str` | Model adı (örn. HS110) |
| `mac` | `str` | MAC adresi |
| `relay_state` | `int` | Güç durumu (0=Kapalı, 1=Açık) |
| `led_off` | `int` | LED durumu (0=Açık, 1=Kapalı) |
| `rssi` | `int` | WiFi sinyal gücü (dBm) |
| `on_time` | `int` | Açık kalma süresi (saniye) |
| `software_version` | `str` | Firmware sürümü |
| `hardware_version` | `str` | Donanım sürümü |

### `EnergyInfo`
Anlık enerji ölçümlerini temsil eder (`get_realtime` yanıtı):

| Alan | Tip | Açıklama |
|------|-----|----------|
| `voltage_mv` | `int` | Voltaj (milivolt) |
| `current_ma` | `int` | Akım (miliamper) |
| `power_mw` | `int` | Güç (miliwatt) |
| `total_wh` | `int` | Toplam tüketim (watt-saat) |

> **Kolay Erişim:** `voltage_v`, `current_a`, `power_w` property'leri ile SI birimlerinde değerlere erişilebilir.

### `DeviceStatus`
Poller tarafından kullanılan birleşik durum anlık görüntüsü:

| Alan | Tip | Açıklama |
|------|-----|----------|
| `online` | `bool` | Cihaz erişilebilir mi |
| `device_info` | `DeviceInfo?` | Sistem bilgisi |
| `energy_info` | `EnergyInfo?` | Enerji bilgisi |
| `timestamp` | `datetime` | Zaman damgası |
| `error` | `str?` | Hata mesajı (varsa) |

---

## 🧪 Testler

Proje hem `pytest` uyumlu hem de bağımsız çalışan test altyapısına sahiptir.

### Hızlı Test (Bağımsız)

```bash
python run_tests.py
```

### pytest ile Çalıştırma

```bash
pip install pytest
pytest -v
```

### Test Kapsamı

| Modül | Test Sayısı | Kapsam |
|-------|-------------|--------|
| `protocol.py` | 6 | XOR şifreleme, çözme, roundtrip, Go vektörleri |
| `device.py` | 7 | Sysinfo, enerji, açma/kapatma, LED, bağlantı hatası |
| `models.py` | 4 | DeviceInfo, EnergyInfo parsed ve boş değerler |
| **Toplam** | **17** | **Tüm testler başarılı ✅** |

---

## 🐍 Programatik Kullanım (API)

Bu projeyi kendi Python scriptlerinizde modül olarak da kullanabilirsiniz:

### Temel Kullanım

```python
from device import HS110Device

# Cihaza bağlan
device = HS110Device("192.168.1.100")

# Sistem bilgisini al
info = device.get_sysinfo()
print(f"Cihaz: {info.alias}, Model: {info.model}")
print(f"Durum: {'Açık' if info.is_on else 'Kapalı'}")

# Prizi aç/kapat
device.turn_on()
device.turn_off()

# LED kontrolü
device.set_led(True)   # LED aç
device.set_led(False)  # LED kapat
```

### Enerji İzleme

```python
# Anlık enerji ölçümü
energy = device.get_realtime_energy()
print(f"Voltaj: {energy.voltage_v:.1f} V")
print(f"Akım:   {energy.current_a:.3f} A")
print(f"Güç:    {energy.power_w:.1f} W")

# Günlük istatistikler
daily_stats = device.get_daily_stats(year=2026, month=3)
for stat in daily_stats:
    print(f"Gün {stat.day}: {stat.energy_wh} Wh")

# Aylık istatistikler
monthly = device.get_monthly_stats(year=2026)
```

### Sürekli İzleme (Poller)

```python
from device import HS110Device
from poller import DevicePoller
from models import DeviceStatus

device = HS110Device("192.168.1.100")

def on_update(status: DeviceStatus):
    if status.online:
        data = status.to_dict()
        print(f"Güç: {data['power_w']:.1f}W, Voltaj: {data['voltage_v']:.1f}V")
    else:
        print(f"Çevrimdışı: {status.error}")

# Context manager ile kullanım
with DevicePoller(device, interval=5.0, callback=on_update) as poller:
    import time
    time.sleep(60)  # 1 dakika izle
```

### Gelişmiş Özellikler

```python
# Geri sayım zamanlayıcısı: 30 saniye sonra kapat
device.set_countdown(seconds=30, action=0)  # 0=kapat, 1=aç

# Cihaz adını değiştir
device.set_alias("Mutfak Prizi")

# WiFi ağlarını tara
networks = device.scan_wifi()

# Bulut bağlantı bilgisi
cloud = device.get_cloud_info()

# Zamanlama kuralları
schedule = device.get_schedule_rules()

# Ham komut gönderme
result = device.send_command({"system": {"get_sysinfo": {}}})
```

---

## 🛡️ Hata Yönetimi

Araç, bağlantı hatalarını zarif bir şekilde yönetir:

```python
try:
    device = HS110Device("192.168.1.100", timeout=3.0)
    info = device.get_sysinfo()
except ConnectionError as e:
    print(f"Bağlantı hatası: {e}")
except TimeoutError as e:
    print(f"Zaman aşımı: {e}")
```

Polling modunda cihaz çevrimdışı olursa, poller otomatik olarak hata durumunu bildirir ve bir sonraki döngüde tekrar dener.

---

## 🤝 Katkıda Bulunma

1. Bu repoyu **fork** edin
2. Yeni bir **feature branch** oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi **commit** edin (`git commit -m 'Yeni özellik ekle'`)
4. Branch'inizi **push** edin (`git push origin feature/yeni-ozellik`)
5. Bir **Pull Request** açın

> Lütfen değişiklik yapmadan önce mevcut testlerin geçtiğinden emin olun: `python run_tests.py`

---


