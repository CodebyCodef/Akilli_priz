"""
Centralized execution logic to call device plugin actions cleanly
without duplicating try-except blocks across every API handler.
"""

from typing import Callable, Any
from fastapi import HTTPException, status
from plugins.registry import get_plugin

def execute_plugin_action(
    brand: str, 
    ip: str, 
    timeout: float, 
    action: Callable[[Any, str, float], Any]
) -> Any:
    """
    Plugin komutunu (action) çalıştırır ve standart hataları HTTPException'a dönüştürür.
    
    Args:
        brand: Cihaz markası (örn: "tplink")
        ip: Cihazın IP adresi
        timeout: Zaman aşımı süresi
        action: Plugin üzerinde çağrılacak metot referansı (örn: plugin.turn_on)
        
    Returns:
        Action sonucunu döndürür.
        
    Raises:
        HTTPException: 400 (Desteklenmeyen marka) veya 503 (Bağlantı hatası)
    """
    try:
        plugin = get_plugin(brand)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        return action(plugin, ip, timeout=timeout)
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cihaza bağlanılamadı ({ip}): {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cihaz işlemi sırasında hata oluştu: {e}",
        )
