"""
Windows WiFi Manager — netsh wlan komutlarını sararak WiFi yönetimi sağlar.

Bu modül, WiFi provisioning akışında kullanılır:
    1. PC'nin çevresindeki WiFi ağlarını tarar
    2. TP-Link AP'lerini (TP-LINK_Smart Plug_XXXX) filtreler
    3. Mevcut bağlı ağı hatırlar
    4. Cihazın AP'sine otomatik bağlanır
    5. İşlem bitince eski ağa geri döner
"""

import subprocess
import re
import time
import logging
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# TP-Link AP SSID deseni (reset sonrası cihazın yaydığı ağ)
TPLINK_AP_PATTERN = re.compile(r"TP-LINK_Smart[ _]Plug[_ ]", re.IGNORECASE)


@dataclass
class ScannedWifi:
    """PC'nin WiFi kartıyla taranan bir ağ."""
    ssid: str
    signal: int  # % cinsinden sinyal gücü
    auth: str  # Kimlik doğrulama tipi (Open, WPA2-Personal, vb.)
    encryption: str  # Şifreleme (CCMP, vb.)
    bssid: str = ""
    channel: int = 0


def scan_wifi_networks() -> list[ScannedWifi]:
    """
    Windows netsh wlan ile çevredeki WiFi ağlarını tarar.

    Returns:
        Taranan WiFi ağlarının listesi.
    """
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            logger.error(f"netsh wlan scan failed: {result.stderr}")
            return []

        return _parse_network_list(result.stdout)

    except subprocess.TimeoutExpired:
        logger.error("netsh wlan scan timed out")
        return []
    except Exception as e:
        logger.error(f"WiFi scan error: {e}")
        return []


def _parse_network_list(output: str) -> list[ScannedWifi]:
    """netsh wlan show networks çıktısını parse eder."""
    networks = []
    current = {}

    for line in output.splitlines():
        line = line.strip()

        # SSID satırı (BSSID değil)
        if line.startswith("SSID") and "BSSID" not in line:
            # Yeni ağ başlıyor
            if current.get("ssid"):
                networks.append(_build_scanned_wifi(current))
            ssid_match = re.match(r"SSID\s*\d*\s*:\s*(.*)", line)
            current = {"ssid": ssid_match.group(1).strip() if ssid_match else ""}

        elif "Authentication" in line or "Kimlik" in line:
            val = line.split(":", 1)[-1].strip()
            current["auth"] = val

        elif "Encryption" in line or "ifreleme" in line.lower():
            val = line.split(":", 1)[-1].strip()
            current["encryption"] = val

        elif "BSSID" in line:
            val = line.split(":", 1)[-1].strip()
            current["bssid"] = val

        elif "Signal" in line or "Sinyal" in line:
            val = line.split(":", 1)[-1].strip().replace("%", "")
            try:
                current["signal"] = int(val)
            except ValueError:
                current["signal"] = 0

        elif "Channel" in line or "Kanal" in line:
            val = line.split(":", 1)[-1].strip()
            try:
                current["channel"] = int(val)
            except ValueError:
                current["channel"] = 0

    # Son ağı ekle
    if current.get("ssid"):
        networks.append(_build_scanned_wifi(current))

    return networks


def _build_scanned_wifi(data: dict) -> ScannedWifi:
    return ScannedWifi(
        ssid=data.get("ssid", ""),
        signal=data.get("signal", 0),
        auth=data.get("auth", ""),
        encryption=data.get("encryption", ""),
        bssid=data.get("bssid", ""),
        channel=data.get("channel", 0),
    )


def discover_tplink_aps() -> list[ScannedWifi]:
    """
    Çevredeki TP-Link akıllı priz AP'lerini bulur.

    Reset sonrası cihaz 'TP-LINK_Smart Plug_XXXX' gibi bir SSID yayar.
    Bu fonksiyon sadece bu desene uyan ağları döndürür.
    """
    all_networks = scan_wifi_networks()
    return [n for n in all_networks if TPLINK_AP_PATTERN.search(n.ssid)]


def get_current_wifi() -> str | None:
    """
    Şu an bağlı olduğumuz WiFi SSID'sini döndürür.

    Returns:
        Bağlı SSID veya None (bağlı değilse).
    """
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        for line in result.stdout.splitlines():
            # "SSID" satırı ama "BSSID" değil
            if "SSID" in line and "BSSID" not in line:
                match = re.match(r"\s*SSID\s*:\s*(.*)", line)
                if match:
                    ssid = match.group(1).strip()
                    if ssid:
                        return ssid
    except Exception as e:
        logger.error(f"Cannot get current WiFi: {e}")
    return None


def connect_to_wifi(ssid: str, password: str | None = None, timeout: int = 15) -> bool:
    """
    Belirtilen WiFi ağına bağlanır.

    TP-Link cihazların AP'si şifresizdir (Open), bu yüzden password
    genellikle None olarak gönderilir.

    Args:
        ssid: Bağlanılacak SSID.
        password: WiFi şifresi (None = açık ağ).
        timeout: Bağlantı bekleme süresi (saniye).

    Returns:
        True = bağlantı başarılı.
    """
    try:
        # Profil zaten varsa yeniden oluşturma (mevcut şifreli profili bozmamak için)
        if not _profile_exists(ssid):
            _ensure_wifi_profile(ssid, password)

        # Bağlan
        result = subprocess.run(
            ["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )

        if result.returncode != 0:
            logger.error(f"WiFi connect failed: {result.stderr}")
            return False

        # Bağlantının gerçekleşmesini bekle
        for _ in range(timeout):
            time.sleep(1)
            current = get_current_wifi()
            if current and current.lower() == ssid.lower():
                logger.info(f"Connected to WiFi: {ssid}")
                return True

        logger.error(f"WiFi connection timed out: {ssid}")
        return False

    except Exception as e:
        logger.error(f"WiFi connect error: {e}")
        return False


def _profile_exists(ssid: str) -> bool:
    """
    Windows'ta belirtilen SSID için kayıtlı WiFi profili olup olmadığını kontrol eder.
    """
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profile", f"name={ssid}"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        return result.returncode == 0
    except Exception:
        return False


def _ensure_wifi_profile(ssid: str, password: str | None = None):
    """
    netsh ile bağlanmak için WiFi profili gerekir.
    Profil yoksa geçici XML profil oluşturur.
    """
    import tempfile
    import os

    if password:
        # WPA2 profili
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
    else:
        # Açık ağ profili (TP-Link AP)
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>"""

    # Geçici dosyaya yaz ve profili ekle
    profile_path = os.path.join(tempfile.gettempdir(), f"wifi_{ssid}.xml")
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(profile_xml)

    try:
        subprocess.run(
            ["netsh", "wlan", "add", "profile", f"filename={profile_path}"],
            capture_output=True, text=True, timeout=5,
        )
    finally:
        os.remove(profile_path)


async def auto_provision(
    device_ap_ssid: str,
    target_ssid: str,
    target_password: str,
    target_key_type: int = 3,
    connect_timeout: int = 15,
) -> dict:
    """
    Tam otomatik WiFi provisioning akışı:

        1. Mevcut WiFi'yi hatırla
        2. Cihazın AP'sine bağlan
        3. Cihaza hedef WiFi bilgilerini gönder (TCP/9999)
        4. Eski WiFi'ye geri dön

    Args:
        device_ap_ssid: Cihazın AP SSID'si (ör: "TP-LINK_Smart Plug_XXXX")
        target_ssid: Cihazın bağlanacağı WiFi ağı
        target_password: Hedef WiFi şifresi
        target_key_type: Şifreleme tipi (3 = WPA/WPA2)
        connect_timeout: Her bağlantı adımı için timeout (saniye)

    Returns:
        İşlem sonucu dict.
    """
    from core.device import HS110Device

    original_wifi = get_current_wifi()
    logger.info(f"Provisioning başlıyor. Mevcut WiFi: {original_wifi}")

    steps = []

    try:
        # Adım 1: Cihazın AP'sine bağlan
        steps.append("Cihazın AP'sine bağlanılıyor...")
        connected = await asyncio.to_thread(
            connect_to_wifi, device_ap_ssid, None, connect_timeout
        )
        if not connected:
            return {
                "success": False,
                "message": f"Cihazın AP'sine ({device_ap_ssid}) bağlanılamadı.",
                "steps": steps,
            }
        steps.append(f"✅ {device_ap_ssid} ağına bağlanıldı.")

        # Adım 2: Kısa bir bekleme (bağlantı stabilize olsun)
        await asyncio.sleep(2)

        # Adım 3: Cihaza WiFi bilgilerini gönder
        steps.append(f"Cihaza '{target_ssid}' ağ bilgileri gönderiliyor...")
        try:
            hs = HS110Device(ip="192.168.0.1", timeout=5.0)
            result = hs.set_wifi(
                ssid=target_ssid,
                password=target_password,
                key_type=target_key_type,
            )
            err_code = (
                result.get("netif", {})
                .get("set_stainfo", {})
                .get("err_code", -1)
            )
            if err_code == 0:
                steps.append(f"✅ WiFi bilgileri cihaza gönderildi.")
            else:
                steps.append(f"❌ WiFi ayarı başarısız (err_code: {err_code})")
                return {
                    "success": False,
                    "message": f"Cihaz WiFi ayarını kabul etmedi (hata: {err_code})",
                    "steps": steps,
                    "raw_response": result,
                }
        except Exception as e:
            steps.append(f"❌ Cihazla iletişim hatası: {e}")
            return {
                "success": False,
                "message": f"Cihaza bağlanılamadı (192.168.0.1): {e}",
                "steps": steps,
            }

    finally:
        # Adım 4: Her durumda eski WiFi'ye geri dön
        if original_wifi:
            steps.append(f"'{original_wifi}' ağına geri dönülüyor...")
            reconnected = await asyncio.to_thread(
                connect_to_wifi, original_wifi, None, connect_timeout
            )
            if reconnected:
                steps.append(f"✅ {original_wifi} ağına geri dönüldü.")
            else:
                steps.append(f"⚠️ {original_wifi} ağına geri dönülemedi. Manuel bağlanın.")

    return {
        "success": True,
        "message": (
            f"Cihaz '{target_ssid}' ağına bağlanıyor. "
            f"Birkaç saniye sonra ağınızda görünecektir."
        ),
        "steps": steps,
    }
