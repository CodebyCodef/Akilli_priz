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
from core.action_executor import execute_plugin_action
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
    mac_address = execute_plugin_action(
        brand=request.brand,
        ip=request.ip,
        timeout=settings.DEVICE_TIMEOUT,
        action=lambda p, ip, t: p.get_mac(ip, timeout=t)
    )

    if not mac_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cihazdan MAC adresi alınamadı.",
        )

    # 2) İsmi cihazın kendisine de yaz (TAPO uygulamasındaki gibi)
    try:
        execute_plugin_action(
            brand=request.brand,
            ip=request.ip,
            timeout=settings.DEVICE_TIMEOUT,
            action=lambda p, ip, t: p.set_alias(ip, request.name, timeout=t)
        )
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
    execute_plugin_action(
        brand=device.brand,
        ip=device.ip_address,
        timeout=settings.DEVICE_TIMEOUT,
        action=lambda p, ip, t: p.set_alias(ip, request.name, timeout=t)
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
