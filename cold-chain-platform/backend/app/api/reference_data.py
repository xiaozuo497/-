from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import auth
from app.core.config import settings
from app.core.db import get_db
from app.models.reference import BoxType, Vehicle
from app.schemas.reference import (
    BoxTypeRead,
    BoxTypeStockUpdate,
    BoxTypeUpsert,
    ImportResult,
    VehicleCreate,
    VehicleRead,
    VehicleStatusUpdate,
)

router = APIRouter(tags=["reference-data"])


@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    return db.scalars(select(Vehicle).order_by(Vehicle.plate_no)).all()


@router.post("/vehicles", response_model=VehicleRead)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    exists = db.scalar(select(Vehicle).where(Vehicle.plate_no == payload.plate_no))
    if exists:
        raise HTTPException(status_code=409, detail="车牌号已存在")
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")
    db.delete(vehicle)
    db.commit()
    return {"ok": True}


@router.patch("/vehicles/{vehicle_id}/status", response_model=VehicleRead)
def update_vehicle_status(
    vehicle_id: UUID,
    payload: VehicleStatusUpdate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    allowed_statuses = {"available", "maintenance", "disabled"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="车辆状态只能是 available、maintenance 或 disabled")
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="车辆不存在")
    vehicle.status = payload.status
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/box-types", response_model=list[BoxTypeRead])
def list_box_types(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher", "warehouse"))):
    return db.scalars(select(BoxType).where(BoxType.enabled.is_(True)).order_by(BoxType.code)).all()


@router.post("/box-types", response_model=BoxTypeRead)
def create_box_type(
    payload: BoxTypeUpsert,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "warehouse")),
):
    exists = db.scalar(select(BoxType).where((BoxType.code == payload.code) | (BoxType.name == payload.name)))
    if exists:
        raise HTTPException(status_code=409, detail="箱型代码或型号已存在")
    box_type = BoxType(**payload.model_dump())
    db.add(box_type)
    db.commit()
    db.refresh(box_type)
    return box_type


@router.delete("/box-types/{box_type_id}")
def delete_box_type(
    box_type_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "warehouse")),
):
    box_type = db.get(BoxType, box_type_id)
    if not box_type:
        raise HTTPException(status_code=404, detail="周转箱不存在")
    box_type.enabled = False
    db.commit()
    return {"ok": True}


@router.patch("/box-types/{box_type_id}/stock", response_model=BoxTypeRead)
def update_box_type_stock(
    box_type_id: UUID,
    payload: BoxTypeStockUpdate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "warehouse")),
):
    box_type = db.get(BoxType, box_type_id)
    if not box_type:
        raise HTTPException(status_code=404, detail="周转箱不存在")
    box_type.stock_quantity = payload.stock_quantity
    db.commit()
    db.refresh(box_type)
    return box_type


@router.post("/vehicles/import", response_model=ImportResult)
def import_vehicles(
    payload: list[VehicleCreate],
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    upserted = 0
    for item in payload:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_no == item.plate_no))
        if not vehicle:
            vehicle = Vehicle(plate_no=item.plate_no)
            db.add(vehicle)
        vehicle.vehicle_type = item.vehicle_type
        vehicle.length_cm = item.length_cm
        vehicle.width_cm = item.width_cm
        vehicle.height_cm = item.height_cm
        vehicle.volume_m3 = item.volume_m3
        vehicle.max_load_kg = item.max_load_kg
        vehicle.temperature_zone = item.temperature_zone
        vehicle.status = item.status
        upserted += 1
    db.commit()
    return ImportResult(upserted=upserted)


@router.post("/box-types/import", response_model=ImportResult)
def import_box_types(
    payload: list[BoxTypeUpsert],
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "warehouse")),
):
    upserted = 0
    for item in payload:
        box_type = db.scalar(select(BoxType).where(BoxType.code == item.code))
        if not box_type:
            box_type = db.scalar(select(BoxType).where(BoxType.name == item.name))
        if not box_type:
            box_type = BoxType(code=item.code)
            db.add(box_type)
        box_type.code = item.code
        box_type.name = item.name
        box_type.length_cm = item.length_cm
        box_type.width_cm = item.width_cm
        box_type.height_cm = item.height_cm
        box_type.inner_size = item.inner_size
        box_type.folded_size = item.folded_size
        box_type.gross_weight_kg = item.gross_weight_kg
        box_type.stock_quantity = item.stock_quantity
        box_type.capacity_desc = item.capacity_desc
        box_type.enabled = item.enabled
        upserted += 1
    db.commit()
    return ImportResult(upserted=upserted)


@router.get("/map-config")
def map_config(_user=Depends(auth.require_roles("admin", "dispatcher", "driver"))):
    return {"amap_key": settings.amap_key, "amap_security_code": settings.amap_security_code}
