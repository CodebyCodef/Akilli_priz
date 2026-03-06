"""
Device CRUD endpoints — kayıt, listeleme, güncelleme, silme.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.database import get_db
from db.db_models import Device
from schemas import (
    DeviceRegisterRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    ActionResponse,
)
from plugins import get_plugin
from config import settings

router = APIRouter(prefix="/api/devices", tags=["Cihaz Yönetimi"])


@router.post(
    "/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni cihaz kaydet",
    description="IP adresi üzerinden cihaza bağlanır, MAC adresini alır ve verilen isimle veritabanına kaydeder.",
)
async def register_device(
    request: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1) Plugin üzerinden cihaza bağlan ve MAC adresini al
    try:
        plugin = get_plugin(request.brand)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        mac_address = plugin.get_mac(request.ip, timeout=settings.DEVICE_TIMEOUT)
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cihaza bağlanılamadı ({request.ip}): {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cihaz bilgisi alınamadı: {e}",
        )

    if not mac_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cihazdan MAC adresi alınamadı.",
        )

    # 2) İsmi cihazın kendisine de yaz (TAPO uygulamasındaki gibi)
    try:
        plugin.set_alias(request.ip, request.name, timeout=settings.DEVICE_TIMEOUT)
    except Exception:
        pass  # İsim yazılamazsa bile DB'ye kaydetmeye devam et

    # 3) Aynı MAC ile kayıtlı cihaz var mı kontrol et
    existing = await db.execute(
        select(Device).where(Device.mac_address == mac_address)
    )
    existing_device = existing.scalar_one_or_none()

    if existing_device:
        # MAC zaten kayıtlı — IP, isim ve markayı güncelle
        existing_device.name = request.name
        existing_device.ip_address = request.ip
        existing_device.brand = request.brand
        await db.flush()
        await db.refresh(existing_device)
        return existing_device

    # 4) Yeni cihaz kaydı oluştur
    new_device = Device(
        mac_address=mac_address,
        name=request.name,
        ip_address=request.ip,
        brand=request.brand,
    )
    db.add(new_device)
    
    try:
        await db.flush()
        await db.refresh(new_device)
        return new_device
    except IntegrityError:
        # Eşzamanlı (concurrent) isteklerde race condition olabilir
        await db.rollback()
        existing = await db.execute(
            select(Device).where(Device.mac_address == mac_address)
        )
        existing_device = existing.scalar_one_or_none()
        
        if existing_device:
            existing_device.name = request.name
            existing_device.ip_address = request.ip
            await db.flush()
            await db.refresh(existing_device)
            return existing_device
        
        raise  # Beklenmeyen başka bir IntegrityError ise fırlat


@router.get(
    "",
    response_model=list[DeviceResponse],
    summary="Tüm cihazları listele",
)
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).order_by(Device.id))
    devices = result.scalars().all()
    return devices


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Tek cihaz bilgisi",
)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cihaz bulunamadı (id={device_id})",
        )
    return device


@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Cihaz ismini güncelle",
)
async def update_device(
    device_id: int,
    request: DeviceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cihaz bulunamadı (id={device_id})",
        )

    # İsmi cihazın kendisine de yaz (plugin üzerinden)
    try:
        plugin = get_plugin(device.brand)
        plugin.set_alias(device.ip_address, request.name, timeout=settings.DEVICE_TIMEOUT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cihaza bağlanılamadı ({device.ip_address}): {e}",
        )

    device.name = request.name
    await db.flush()
    await db.refresh(device)
    return device


@router.delete(
    "/{device_id}",
    response_model=ActionResponse,
    summary="Cihaz kaydını sil",
)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cihaz bulunamadı (id={device_id})",
        )

    await db.delete(device)
    return ActionResponse(
        success=True,
        message=f"'{device.name}' cihazı silindi.",
    )
