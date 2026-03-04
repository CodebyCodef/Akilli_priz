"""
TP-Link Cihaz Keşif Modülü — UDP broadcast ile ağdaki cihazları bulur.

TP-Link akıllı ev cihazları, UDP port 9999 üzerinden broadcast olarak
gönderilen get_sysinfo komutuna yanıt verir. Bu modül bu mekanizmayı
kullanarak ağdaki tüm TP-Link cihazları otomatik olarak keşfeder.

Nasıl Çalışıyor:
    1. protocol.py'deki encrypt() ile get_sysinfo komutunu şifreler
    2. 255.255.255.255:9999 adresine UDP broadcast olarak gönderir
    3. Ağdaki tüm TP-Link cihazlar kendi bilgileriyle (IP, alias, model, MAC) yanıt verir
    4. Yanıtlar protocol.py'deki decrypt() ile çözülür ve listeye derlenir

Önemli Fark — TCP vs UDP Şifreleme:
    TCP: [4-byte length header] + [XOR payload]  → protocol.py bunu yapar
    UDP: [XOR payload only, header yok]           → bu modülde ayrı fonksiyon
    TP-Link cihazlar UDP yanıtında bazen header ekler, bazen eklemez.
    Bu yüzden yanıt çözümünde otomatik algılama yapılır.
"""

import json
import socket
import struct
import logging
import asyncio
from dataclasses import dataclass

from core.protocol import INITIAL_KEY

logger = logging.getLogger(__name__)

# TP-Link cihazları TCP/UDP port 9999 üzerinden haberleşir
TPLINK_PORT = 9999

# UDP broadcast adresi — tüm ağa yayın yapar
BROADCAST_ADDR = "255.255.255.255"

# Keşif komutu — tüm TP-Link cihazları bu komuta yanıt verir
DISCOVERY_QUERY = '{"system":{"get_sysinfo":{}}}'


@dataclass
class DiscoveredDevice:
    """Keşfedilen cihaz bilgisi."""
    ip: str
    alias: str = ""
    model: str = ""
    mac: str = ""
    device_id: str = ""
    is_on: bool = False
    rssi: int = 0
    hardware_version: str = ""
    software_version: str = ""


def _xor_encrypt(message: str) -> bytes:
    """
    XOR Autokey şifreleme — protocol.py ile aynı algoritma ama
    UDP için 4-byte length header EKLENMEZ.

    protocol.py'deki encrypt() fonksiyonu TCP içindir ve başına
    4-byte Big Endian header koyar. UDP broadcast'te bu header
    gönderilmez, sadece XOR payload gönderilir.

    Algoritma: key=0xAB → her karakter: encrypted = char XOR key, key = encrypted
    """
    key = INITIAL_KEY  # protocol.py'den 0xAB
    result = bytearray()
    for char in message:
        encrypted_byte = ord(char) ^ key
        key = encrypted_byte
        result.append(encrypted_byte & 0xFF)
    return bytes(result)


def _xor_decrypt_auto(data: bytes) -> str:
    """
    XOR Autokey çözme — protocol.py ile aynı algoritma.

    Bazı cihazlar UDP yanıtına 4-byte header ekler, bazıları eklemez.
    Bu fonksiyon otomatik algılama yapar:
      - İlk 4 byte'ı length olarak parse eder
      - Eğer len(data) - 4 == length ise → header var, atla
      - Değilse → header yok, tüm veriyi çöz

    Algoritma: key=0xAB → her byte: decrypted = byte XOR key, key = byte
    """
    if len(data) > 4:
        potential_length = struct.unpack(">I", data[:4])[0]
        if potential_length == len(data) - 4:
            data = data[4:]  # TCP-style header var, atla

    key = INITIAL_KEY
    result = []
    for byte in data:
        decrypted = byte ^ key
        key = byte
        result.append(chr(decrypted))
    return "".join(result)


def discover_devices(timeout: float = 3.0) -> list[DiscoveredDevice]:
    """
    UDP broadcast ile ağdaki TP-Link cihazları keşfeder.

    Akış:
        1. UDP socket aç, broadcast izni ver
        2. encrypt(get_sysinfo) → 255.255.255.255:9999'a gönder
        3. timeout süresince yanıtları topla
        4. Her yanıtı decrypt edip cihaz listesine ekle

    Args:
        timeout: Yanıt bekleme süresi (saniye). Varsayılan 3s.
                 Büyük ağlarda 5-10s önerilir.

    Returns:
        Bulunan TP-Link cihazların listesi.
    """
    devices = []
    seen_ips = set()

    try:
        # 1. UDP socket — broadcast izinli
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # 2. Şifreli keşif komutunu broadcast olarak gönder
        encrypted_query = _xor_encrypt(DISCOVERY_QUERY)
        sock.sendto(encrypted_query, (BROADCAST_ADDR, TPLINK_PORT))
        logger.info(
            f"UDP keşif gönderildi → {BROADCAST_ADDR}:{TPLINK_PORT} "
            f"({len(encrypted_query)} byte)"
        )

        # 3. Yanıtları timeout'a kadar topla
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]

                # Aynı IP'den birden fazla yanıt gelebilir, atla
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)

                # 4. Yanıtı çöz ve parse et
                try:
                    decrypted = _xor_decrypt_auto(data)
                    response = json.loads(decrypted)
                    info = response.get("system", {}).get("get_sysinfo", {})

                    device = DiscoveredDevice(
                        ip=ip,
                        alias=info.get("alias", ""),
                        model=info.get("model", ""),
                        mac=info.get("mac", ""),
                        device_id=info.get("deviceId", ""),
                        is_on=info.get("relay_state", 0) == 1,
                        rssi=info.get("rssi", 0),
                        hardware_version=info.get("hw_ver", ""),
                        software_version=info.get("sw_ver", ""),
                    )
                    devices.append(device)
                    logger.info(
                        f"✓ Cihaz bulundu: {device.alias or '(isimsiz)'} "
                        f"({ip}) — {device.model}"
                    )

                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Yanıt çözülemedi ({ip}): {e}")

            except socket.timeout:
                # Timeout → tarama bitti
                break

        sock.close()

    except OSError as e:
        logger.error(f"UDP keşif hatası: {e}")

    logger.info(f"Keşif tamamlandı → {len(devices)} cihaz bulundu")
    return devices


async def discover_devices_async(timeout: float = 3.0) -> list[DiscoveredDevice]:
    """
    Async wrapper — blocking UDP taramayı thread pool'da çalıştırır.
    FastAPI endpoint'leri async olduğu için bu wrapper gereklidir.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, discover_devices, timeout)
