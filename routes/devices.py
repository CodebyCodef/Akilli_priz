"""
Device CRUD endpoints — kayıt, listeleme, güncelleme, silme.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from db_models import Device
from schemas import (
    DeviceRegisterRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    ActionResponse,
)
from device import HS110Device
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
    # 1) Cihaza TCP ile bağlan ve MAC adresini al
    try:
        hs_device = HS110Device(ip=request.ip, timeout=settings.DEVICE_TIMEOUT)
        info = hs_device.get_sysinfo()
        mac_address = info.mac
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

    # 2) Aynı MAC ile kayıtlı cihaz var mı kontrol et
    existing = await db.execute(
        select(Device).where(Device.mac_address == mac_address)
    )
    existing_device = existing.scalar_one_or_none()

    if existing_device:
        # MAC zaten kayıtlı — IP ve ismi güncelle
        existing_device.name = request.name
        existing_device.ip_address = request.ip
        await db.flush()
        await db.refresh(existing_device)
        return existing_device

    # 3) Yeni cihaz kaydı oluştur
    new_device = Device(
        mac_address=mac_address,
        name=request.name,
        ip_address=request.ip,
    )
    db.add(new_device)
    await db.flush()
    await db.refresh(new_device)
    return new_device


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
