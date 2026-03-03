"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Device CRUD Schemas
# ─────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    """POST /api/devices/register — yeni cihaz kaydı."""
    ip: str = Field(..., description="Cihazın yerel ağdaki IP adresi", examples=["192.168.1.100"])
    name: str = Field(..., description="Cihaza verilecek isim", examples=["Salon Priz"])


class DeviceUpdateRequest(BaseModel):
    """PUT /api/devices/{id} — cihaz ismini güncelle."""
    name: str = Field(..., description="Yeni cihaz ismi", examples=["Mutfak Priz"])


class DeviceResponse(BaseModel):
    """Cihaz bilgisi yanıtı."""
    id: int
    mac_address: str
    name: str
    ip_address: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Device Info / Control Schemas
# ─────────────────────────────────────────────

class DeviceInfoResponse(BaseModel):
    """Cihaz sistem bilgisi yanıtı (get_sysinfo)."""
    alias: str = ""
    model: str = ""
    mac: str = ""
    is_on: bool = False
    is_led_on: bool = False
    rssi: int = 0
    on_time: int = 0
    software_version: str = ""
    hardware_version: str = ""


class EnergyResponse(BaseModel):
    """Gerçek zamanlı enerji ölçümü yanıtı."""
    voltage_v: float = 0.0
    current_a: float = 0.0
    power_w: float = 0.0
    total_wh: int = 0


class ActionResponse(BaseModel):
    """Genel aksiyon yanıtı."""
    success: bool
    message: str
    data: Optional[dict] = None


# ─────────────────────────────────────────────
# WiFi Provisioning Schemas
# ─────────────────────────────────────────────

class WifiNetwork(BaseModel):
    """Taranan WiFi ağ bilgisi."""
    ssid: str
    key_type: int = Field(description="0=Açık, 2=WEP, 3=WPA/WPA2")
    rssi: int = Field(description="Sinyal gücü (dBm)")


class WifiSetupRequest(BaseModel):
    """WiFi bağlantı isteği — cihazı ağa bağlar."""
    ssid: str = Field(..., description="WiFi ağ adı", examples=["MyWiFi"])
    password: str = Field(..., description="WiFi şifresi", examples=["password123"])
    key_type: int = Field(default=3, description="Şifreleme tipi: 0=Açık, 2=WEP, 3=WPA/WPA2")

