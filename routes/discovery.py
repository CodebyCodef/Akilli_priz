"""
Cihaz keşif endpoint'i — ağdaki TP-Link cihazları UDP broadcast ile otomatik bulur.

Akış:
    Frontend → GET /api/devices/discover
           → Backend: UDP broadcast 255.255.255.255:9999
           → Ağdaki tüm TP-Link cihazlar yanıt verir
           → Backend: yanıtları çözüp JSON listesi döner
"""

from fastapi import APIRouter

from core.discovery import discover_devices_async
from schemas import DiscoveredDeviceResponse

router = APIRouter(prefix="/api/devices", tags=["Cihaz Keşfi"])


@router.get(
    "/discover",
    response_model=list[DiscoveredDeviceResponse],
    summary="Ağdaki TP-Link cihazları otomatik keşfet",
    description=(
        "UDP broadcast ile yerel ağdaki tüm TP-Link akıllı priz cihazlarını "
        "otomatik bulur. IP adresini bilmenize gerek kalmaz!\n\n"
        "**Nasıl çalışır:**\n"
        "1. `255.255.255.255:9999` adresine şifreli `get_sysinfo` komutu gönderilir\n"
        "2. Ağdaki tüm TP-Link cihazlar kendi bilgileriyle yanıt verir\n"
        "3. IP adresleri ve cihaz isimleri (alias) JSON listesi olarak döner\n\n"
        "**timeout** parametresi ile tarama süresini ayarlayabilirsiniz (varsayılan 3s)."
    ),
)
async def discover(timeout: float = 3.0):
    """
    Query params:
        timeout: Tarama süresi saniye cinsinden (varsayılan 3.0).
                 Büyük ağlarda 5-10s önerilir.

    Returns:
        Bulunan cihazların IP, alias, model, MAC bilgilerini içeren liste.
    """
    devices = await discover_devices_async(timeout=timeout)
    return [
        DiscoveredDeviceResponse(
            ip=d.ip,
            alias=d.alias,
            model=d.model,
            mac=d.mac,
            device_id=d.device_id,
            is_on=d.is_on,
            rssi=d.rssi,
            hardware_version=d.hardware_version,
            software_version=d.software_version,
        )
        for d in devices
    ]
