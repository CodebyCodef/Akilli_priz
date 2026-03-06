"""
Plugin Registry — marka bazlı akıllı cihaz plugin yönetimi.

Yeni marka eklemek için:
    1. plugins/yeni_marka.py oluştur (SmartDevicePlugin'den türet)
    2. Aşağıdaki _PLUGINS sözlüğüne ekle
"""

from plugins.base import SmartDevicePlugin
from plugins.tplink import TPLinkPlugin

# Kayıtlı plugin'ler — yeni marka eklemek için buraya bir satır ekle
_PLUGINS: dict[str, SmartDevicePlugin] = {
    "tplink": TPLinkPlugin(),
}


def get_plugin(brand: str) -> SmartDevicePlugin:
    """
    Marka adına göre doğru plugin'i döndürür.

    Args:
        brand: Marka adı (ör: "tplink", "tuya", "xiaomi")

    Returns:
        İlgili SmartDevicePlugin instance'ı.

    Raises:
        ValueError: Desteklenmeyen marka.
    """
    plugin = _PLUGINS.get(brand.lower())
    if not plugin:
        supported = ", ".join(_PLUGINS.keys())
        raise ValueError(
            f"Desteklenmeyen marka: '{brand}'. "
            f"Desteklenen markalar: {supported}"
        )
    return plugin


def list_supported_brands() -> list[str]:
    """Desteklenen marka listesini döndürür."""
    return list(_PLUGINS.keys())
