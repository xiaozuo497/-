from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api import auth
from app.core.db import get_db
from datetime import datetime, time, timezone

from app.models.order import DeliveryRecord, DispatchAssignment, OperationException, Order
from app.schemas.order import (
    DeliveryComplete,
    DeliveryRecordRead,
    DispatchAssignmentRead,
    DispatchCreate,
    DispatchStatusUpdate,
    OperationExceptionCreate,
    OperationExceptionRead,
    OrderCreate,
    OrderRead,
    OrderUpdate,
)
from app.seed import seed_box_types, seed_orders
from app.services.geocode_service import geocode_destination

router = APIRouter(prefix="/orders", tags=["orders"])


def order_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        order_no=order.order_no,
        origin_name=order.origin_name,
        destination_name=order.destination_name,
        destination_address=order.destination_address,
        lng=float(order.lng) if order.lng is not None else None,
        lat=float(order.lat) if order.lat is not None else None,
        geocode_source=order.geocode_source,
        geocode_status=order.geocode_status,
        box_type_id=order.box_type_id,
        box_type_code=order.box_type.code if order.box_type else None,
        box_type_name=order.box_type.name if order.box_type else None,
        box_count=order.box_count,
        unit_weight_kg=float(order.unit_weight_kg),
        ready_time=order.ready_time,
        due_time=order.due_time,
        contact_name=order.contact_name,
        contact_phone=order.contact_phone,
        status=order.status,
    )


def fill_coordinates(order: Order) -> None:
    if order.lng is not None and order.lat is not None:
        order.geocode_source = order.geocode_source or "manual"
        order.geocode_status = "verified"
        return
    point = geocode_destination(order.destination_name, order.destination_address)
    order.lng = point["lng"]
    order.lat = point["lat"]
    order.geocode_source = point["source"]
    order.geocode_status = "needs_review" if point["source"] == "fallback" else "verified"


@router.get("", response_model=list[OrderRead])
def list_orders(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    rows = db.scalars(
        select(Order).options(selectinload(Order.box_type)).order_by(Order.due_time.asc().nulls_last())
    ).all()
    return [order_read(order) for order in rows]


@router.post("", response_model=OrderRead)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    exists = db.scalar(select(Order).where(Order.order_no == payload.order_no))
    if exists:
        raise HTTPException(status_code=409, detail="订单号已存在")
    order = Order(**payload.model_dump())
    fill_coordinates(order)
    db.add(order)
    db.commit()
    db.refresh(order)
    db.refresh(order, attribute_names=["box_type"])
    return order_read(order)


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(
    order_id: str,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    if order.lng is None or order.lat is None:
        fill_coordinates(order)
    elif payload.lng is not None or payload.lat is not None or payload.geocode_status == "verified":
        order.geocode_source = "manual"
        order.geocode_status = "verified"
    db.commit()
    db.refresh(order)
    db.refresh(order, attribute_names=["box_type"])
    return order_read(order)


@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    db.delete(order)
    db.commit()
    return {"ok": True}


@router.post("/demo")
def load_demo_orders(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    seed_box_types(db)
    changed = seed_orders(db)
    db.commit()
    return {"ok": True, "created": changed}


@router.get("/deliveries", response_model=list[DeliveryRecordRead])
def list_delivery_records(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher", "driver"))):
    return db.scalars(select(DeliveryRecord).order_by(DeliveryRecord.actual_arrival.desc())).all()


@router.post("/deliveries/complete", response_model=DeliveryRecordRead)
def complete_delivery(
    payload: DeliveryComplete,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher", "driver")),
):
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    record = db.scalar(select(DeliveryRecord).where(DeliveryRecord.order_id == payload.order_id))
    if not record:
        record = DeliveryRecord(order_id=payload.order_id)
        db.add(record)
    record.vehicle_id = payload.vehicle_id
    record.actual_arrival = payload.actual_arrival or datetime.now(timezone.utc)
    record.status = "delivered"
    record.note = payload.note
    order.status = "delivered"
    assignment = db.scalar(select(DispatchAssignment).where(DispatchAssignment.order_id == payload.order_id))
    if assignment:
        assignment.status = "delivered"
    db.commit()
    db.refresh(record)
    return record


def planned_arrival_today(label: str | None) -> datetime | None:
    if not label:
        return None
    try:
        hour, minute = [int(part) for part in label.split(":", 1)]
    except ValueError:
        return None
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today, time(hour, minute), tzinfo=timezone.utc)


@router.post("/dispatch", response_model=list[DispatchAssignmentRead])
def create_dispatch(
    payload: DispatchCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    created: list[DispatchAssignment] = []
    for route in payload.solution.get("routes", []):
        vehicle_id = route.get("vehicle_id")
        for stop in route.get("stops", []):
            order_id = stop.get("order_id")
            if not order_id or not vehicle_id:
                continue
            assignment = db.scalar(select(DispatchAssignment).where(DispatchAssignment.order_id == order_id))
            if not assignment:
                assignment = DispatchAssignment(order_id=order_id, vehicle_id=vehicle_id)
                db.add(assignment)
            assignment.optimization_task_id = payload.task_id
            assignment.vehicle_id = vehicle_id
            assignment.route_sequence = int(stop.get("sequence") or 0)
            assignment.planned_arrival = planned_arrival_today(stop.get("arrival_time"))
            assignment.status = "dispatched"
            order = db.get(Order, order_id)
            if order:
                order.status = "dispatched"
            created.append(assignment)
    db.commit()
    for assignment in created:
        db.refresh(assignment)
    return created


@router.get("/dispatch", response_model=list[DispatchAssignmentRead])
def list_dispatch_assignments(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher", "driver"))):
    return db.scalars(select(DispatchAssignment).order_by(DispatchAssignment.created_at.desc())).all()


@router.patch("/dispatch/{assignment_id}", response_model=DispatchAssignmentRead)
def update_dispatch_status(
    assignment_id: str,
    payload: DispatchStatusUpdate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher", "driver")),
):
    assignment = db.get(DispatchAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="派单任务不存在")
    assignment.status = payload.status
    order = db.get(Order, assignment.order_id)
    if order:
        order.status = payload.status
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/exceptions", response_model=OperationExceptionRead)
def create_operation_exception(
    payload: OperationExceptionCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher", "driver", "warehouse")),
):
    exception = OperationException(
        order_id=payload.order_id,
        vehicle_id=payload.vehicle_id,
        exception_type=payload.exception_type,
        description=payload.description,
        status="reoptimize_needed" if payload.trigger_reoptimization else "open",
    )
    db.add(exception)
    if payload.order_id:
        order = db.get(Order, payload.order_id)
        if order:
            order.status = "exception"
    db.commit()
    db.refresh(exception)
    return exception


@router.get("/exceptions", response_model=list[OperationExceptionRead])
def list_operation_exceptions(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher", "warehouse"))):
    return db.scalars(select(OperationException).order_by(OperationException.created_at.desc())).all()
from app.api import auth
