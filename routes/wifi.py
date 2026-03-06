"""
WiFi provisioning endpoints — cihazı ağa bağlama (otomatik + manuel).

Yeni Akış (Otomatik):
    1. GET  /api/wifi/discover  → PC'nin WiFi kartıyla TP-Link AP'lerini bul
    2. POST /api/wifi/provision → Otomatik: AP'ye bağlan → credential gönder → eski ağa dön

Eski Akış (Manuel):
    3. GET  /api/wifi/scan      → Cihazın kendi WiFi taraması (AP'ye zaten bağlıyken)
    4. POST /api/wifi/setup     → Cihaza WiFi bilgisi gönder (AP'ye zaten bağlıyken)
"""

from fastapi import APIRouter, HTTPException, status

from schemas import (
    WifiNetwork,
    WifiSetupRequest,
    ActionResponse,
    ScannedWifiResponse,
    WifiProvisionRequest,
    WifiProvisionResponse,
)
from core.device import HS110Device
from core.wifi_manager import (
    scan_wifi_networks,
    discover_tplink_aps,
    auto_provision,
    TPLINK_AP_PATTERN,
)
from config import settings

router = APIRouter(prefix="/api/wifi", tags=["WiFi Provisioning"])

# Cihaz AP modundayken varsayılan IP adresi
DEFAULT_AP_IP = "192.168.0.1"


# ─────────────────────────────────────────────
# YENİ: Otomatik Provisioning Endpoint'leri
# ─────────────────────────────────────────────

@router.get(
    "/discover",
    response_model=list[ScannedWifiResponse],
    summary="PC WiFi taramasıyla TP-Link AP'lerini bul",
    description=(
        "PC'nin WiFi kartını kullanarak çevredeki tüm WiFi ağlarını tarar.\n\n"
        "TP-Link akıllı priz AP'leri (TP-LINK_Smart Plug_XXXX) otomatik işaretlenir.\n"
        "Reset sonrası bir cihaz bu listede `is_tplink_ap: true` olarak görünür."
    ),
)
async def discover_aps():
    """
    PC'nin WiFi kartıyla çevredeki ağları tarar.
    TP-Link AP'leri is_tplink_ap=true olarak işaretlenir.
    """
    networks = scan_wifi_networks()

    if not networks:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WiFi taraması yapılamadı. WiFi kartınızın açık olduğundan emin olun.",
        )

    return [
        ScannedWifiResponse(
            ssid=n.ssid,
            signal=n.signal,
            auth=n.auth,
            is_tplink_ap=bool(TPLINK_AP_PATTERN.search(n.ssid)),
        )
        for n in networks
        if n.ssid  # Boş SSID'leri atla
    ]


@router.post(
    "/provision",
    response_model=WifiProvisionResponse,
    summary="Cihazı otomatik olarak WiFi ağına bağla",
    description=(
        "Tam otomatik akış:\n\n"
        "1. PC'nin WiFi'si cihazın AP'sine bağlanır\n"
        "2. Cihaza hedef WiFi bilgileri gönderilir\n"
        "3. PC eski WiFi'sine geri döner\n\n"
        "**Not:** Bu işlem ~30 saniye sürebilir. İşlem sırasında PC'nin "
        "internet bağlantısı geçici olarak kesilir."
    ),
)
async def provision_device(request: WifiProvisionRequest):
    """
    Otomatik WiFi provisioning — arka planda tüm adımları yapar.
    """
    result = await auto_provision(
        device_ap_ssid=request.device_ap_ssid,
        target_ssid=request.target_ssid,
        target_password=request.target_password,
        target_key_type=request.target_key_type,
    )

    return WifiProvisionResponse(
        success=result["success"],
        message=result["message"],
        steps=result.get("steps", []),
        data=result.get("raw_response"),
    )


# ─────────────────────────────────────────────
# ESKİ: Manuel Provisioning Endpoint'leri
# (AP'ye zaten bağlıyken kullanılır)
# ─────────────────────────────────────────────

@router.get(
    "/scan",
    response_model=list[WifiNetwork],
    summary="Cihazın kendi WiFi taraması",
    description=(
        "Cihazın çevresindeki WiFi ağlarını listeler. "
        "Cihaz AP modundayken ve PC o AP'ye bağlıyken çağırın."
    ),
)
async def scan_wifi(ip: str = DEFAULT_AP_IP):
    """
    Manuel mod: Cihazın AP'sine zaten bağlıyken cihazın gördüğü ağları listeler.
    """
    try:
        hs = HS110Device(ip=ip, timeout=settings.DEVICE_TIMEOUT)
        networks = hs.get_scan_wifi_list()
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cihaza bağlanılamadı ({ip}): {e}. "
                   f"PC'nizin WiFi'sini cihazın AP'sine bağladığınızdan emin olun.",
        )

    return [WifiNetwork(**n) for n in networks]


@router.post(
    "/setup",
    response_model=ActionResponse,
    summary="Cihazı WiFi ağına bağla (manuel)",
    description=(
        "Manuel mod: Cihazın AP'sine zaten bağlıyken WiFi bilgilerini gönderir. "
        "Otomatik akış için /api/wifi/provision kullanın."
    ),
)
async def setup_wifi(request: WifiSetupRequest, ip: str = DEFAULT_AP_IP):
    """
    Manuel mod: Cihaza doğrudan WiFi bilgisi gönderir.
    """
    try:
        hs = HS110Device(ip=ip, timeout=5.0)
        result = hs.set_wifi(
            ssid=request.ssid,
            password=request.password,
            key_type=request.key_type,
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cihaza bağlanılamadı ({ip}): {e}. "
                   f"PC'nizin WiFi'sini cihazın AP'sine bağladığınızdan emin olun.",
        )

    err_code = result.get("netif", {}).get("set_stainfo", {}).get("err_code", -1)

    if err_code == 0:
        return ActionResponse(
            success=True,
            message=f"Cihaz '{request.ssid}' ağına bağlanıyor. "
                    f"Birkaç saniye sonra cihaz yeni IP'siyle ağınızda görünecektir.",
        )
    else:
        return ActionResponse(
            success=False,
            message=f"WiFi ayarı başarısız oldu (hata kodu: {err_code}).",
            data=result,
        )
