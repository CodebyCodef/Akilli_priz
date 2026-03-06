"""
TP-Link Plugin — mevcut HS110Device'ı SmartDevicePlugin arayüzüne sarar.

Bu plugin, TP-Link cihazlarıyla iletişimi (XOR autokey + TCP/9999)
standart plugin arayüzü üzerinden sunar.
"""

from plugins.base import SmartDevicePlugin, PluginDeviceInfo, PluginEnergyInfo
from core.device import HS110Device


class TPLinkPlugin(SmartDevicePlugin):
    """TP-Link HS110/HS100 akıllı priz plugin'i."""

    def _device(self, ip: str, timeout: float) -> HS110Device:
        """HS110Device instance'ı oluşturur."""
        return HS110Device(ip=ip, timeout=timeout)

    def turn_on(self, ip: str, timeout: float = 2.0) -> bool:
        hs = self._device(ip, timeout)
        hs.turn_on()
        return True

    def turn_off(self, ip: str, timeout: float = 2.0) -> bool:
        hs = self._device(ip, timeout)
        hs.turn_off()
        return True

    def get_info(self, ip: str, timeout: float = 2.0) -> PluginDeviceInfo:
        hs = self._device(ip, timeout)
        info = hs.get_sysinfo()
        return PluginDeviceInfo(
            alias=info.alias,
            model=info.model,
            mac=info.mac,
            is_on=info.is_on,
            is_led_on=info.is_led_on,
            rssi=info.rssi,
            on_time=info.on_time,
            software_version=info.software_version,
            hardware_version=info.hardware_version,
        )

    def get_energy(self, ip: str, timeout: float = 2.0) -> PluginEnergyInfo:
        hs = self._device(ip, timeout)
        energy = hs.get_realtime_energy()
        return PluginEnergyInfo(
            voltage_v=energy.voltage_v,
            current_a=energy.current_a,
            power_w=energy.power_w,
            total_wh=energy.total_wh,
        )

    def set_led(self, ip: str, on: bool, timeout: float = 2.0) -> bool:
        hs = self._device(ip, timeout)
        hs.set_led(on)
        return True

    def get_mac(self, ip: str, timeout: float = 2.0) -> str:
        hs = self._device(ip, timeout)
        info = hs.get_sysinfo()
        return info.mac

    def set_alias(self, ip: str, alias: str, timeout: float = 2.0) -> bool:
        hs = self._device(ip, timeout)
        hs.set_alias(alias)
        return True
