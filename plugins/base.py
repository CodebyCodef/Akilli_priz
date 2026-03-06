"""
SmartDevicePlugin — tüm akıllı priz markalarının uyması gereken soyut şablon.

Yeni marka eklemek için bu sınıftan türetip tüm abstractmethod'ları implemente edin.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PluginDeviceInfo:
    """Plugin'den dönen standart cihaz bilgisi."""
    alias: str = ""
    model: str = ""
    mac: str = ""
    is_on: bool = False
    is_led_on: bool = False
    rssi: int = 0
    on_time: int = 0
    software_version: str = ""
    hardware_version: str = ""


@dataclass
class PluginEnergyInfo:
    """Plugin'den dönen standart enerji bilgisi."""
    voltage_v: float = 0.0
    current_a: float = 0.0
    power_w: float = 0.0
    total_wh: int = 0


class SmartDevicePlugin(ABC):
    """
    Tüm akıllı priz markalarının uyması gereken standart şablon.

    Her yeni marka (Tuya, Xiaomi, Sonoff, vb.) bu sınıftan türetilir.
    Route'lar sadece bu arayüzü kullanır — markanın iç protokolünü bilmez.
    """

    @abstractmethod
    def turn_on(self, ip: str, timeout: float = 2.0) -> bool:
        """Prizi açar. Başarılıysa True döner."""
        pass

    @abstractmethod
    def turn_off(self, ip: str, timeout: float = 2.0) -> bool:
        """Prizi kapatır. Başarılıysa True döner."""
        pass

    @abstractmethod
    def get_info(self, ip: str, timeout: float = 2.0) -> PluginDeviceInfo:
        """Cihaz sistem bilgilerini döndürür."""
        pass

    @abstractmethod
    def get_energy(self, ip: str, timeout: float = 2.0) -> PluginEnergyInfo:
        """Anlık enerji ölçümünü döndürür."""
        pass

    @abstractmethod
    def set_led(self, ip: str, on: bool, timeout: float = 2.0) -> bool:
        """LED durumunu ayarlar. Başarılıysa True döner."""
        pass

    @abstractmethod
    def get_mac(self, ip: str, timeout: float = 2.0) -> str:
        """Cihazın MAC adresini döndürür (kayıt için)."""
        pass

    @abstractmethod
    def set_alias(self, ip: str, alias: str, timeout: float = 2.0) -> bool:
        """Cihaz takma adını değiştirir. Başarılıysa True döner."""
        pass
