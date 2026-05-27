from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import auth
from app.core.db import get_db
from app.models.optimization import OptimizationSolution, OptimizationTask
from app.models.order import Order
from app.models.reference import BoxType, Vehicle
from app.schemas.optimization import OptimizationTaskCreate, OptimizationTaskRead, SolutionSummary
from app.services.vrptw_solver import solve_vrptw

router = APIRouter(prefix="/optimization", tags=["optimization"])


def box_volume_m3(box_type: BoxType) -> float:
    return float(box_type.length_cm) * float(box_type.width_cm) * float(box_type.height_cm) / 1_000_000


def format_box_mix(shortage_m3: float, box_types: list[BoxType]) -> str:
    usable = sorted(
        [box_type for box_type in box_types if box_volume_m3(box_type) > 0],
        key=box_volume_m3,
        reverse=True,
    )
    mixes = []
    for box_type in usable[:3]:
        count = max(1, int(-(-shortage_m3 // box_volume_m3(box_type))))
        mixes.append(f"{box_type.name} × {count}")

    if len(usable) >= 2:
        largest, smallest = usable[0], usable[-1]
        largest_count = max(0, int(shortage_m3 // box_volume_m3(largest)))
        remaining = max(0, shortage_m3 - largest_count * box_volume_m3(largest))
        smallest_count = max(1, int(-(-remaining // box_volume_m3(smallest)))) if remaining else 0
        if largest_count or smallest_count:
            mixes.append(f"{largest.name} × {largest_count} + {smallest.name} × {smallest_count}")

    return "；".join(mixes) if mixes else "无可用箱型"


def validate_box_inventory_volume(orders: list[Order], box_types: list[BoxType]) -> None:
    box_type_by_id = {box_type.id: box_type for box_type in box_types}
    required_by_type: dict = {}
    for order in orders:
        if not order.box_type_id:
            raise HTTPException(status_code=400, detail=f"订单 {order.order_no} 缺少箱型，需先复核")
        required_by_type[order.box_type_id] = required_by_type.get(order.box_type_id, 0) + int(order.box_count)

    shortages = []
    for box_type_id, required_count in required_by_type.items():
        box_type = box_type_by_id.get(box_type_id)
        if not box_type:
            shortages.append(f"{box_type_id}: 需要 {required_count} 个，可用 0 个")
            continue
        available_count = max(0, int(box_type.stock_quantity))
        if available_count < required_count:
            shortages.append(f"{box_type.code}/{box_type.name}: 需要 {required_count} 个，可用 {available_count} 个")

    if shortages:
        raise HTTPException(status_code=400, detail="周转箱库存不足：" + "；".join(shortages))

    fallback_volume = 0.6 * 0.4 * 0.22
    required_volume = 0.0
    for order in orders:
        box_type = box_type_by_id.get(order.box_type_id)
        unit_volume = box_volume_m3(box_type) if box_type else fallback_volume
        required_volume += int(order.box_count) * unit_volume

    available_volume = sum(max(0, int(box_type.stock_quantity)) * box_volume_m3(box_type) for box_type in box_types)
    if available_volume + 1e-9 >= required_volume:
        return

    shortage = required_volume - available_volume
    mixes = format_box_mix(shortage, box_types)
    raise HTTPException(
        status_code=400,
        detail=(
            f"周转箱不足以装载所有货物：需求体积 {required_volume:.2f} m³，"
            f"现有库存可装载 {available_volume:.2f} m³，缺口 {shortage:.2f} m³。"
            f"可补充组合：{mixes}"
        ),
    )


@router.post("/tasks", response_model=OptimizationTaskRead)
def create_optimization_task(
    payload: OptimizationTaskCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    task = OptimizationTask(
        task_no=f"OPT-{uuid4().hex[:10].upper()}",
        name=payload.name,
        status="queued",
        objective=payload.objective,
        order_count=len(payload.order_ids),
        vehicle_count=len(payload.vehicle_ids),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks", response_model=list[OptimizationTaskRead])
def list_optimization_tasks(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    return db.scalars(select(OptimizationTask).order_by(OptimizationTask.created_at.desc()).limit(50)).all()


@router.post("/run")
def run_optimization(
    payload: OptimizationTaskCreate,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher")),
):
    orders_query = select(Order)
    if payload.order_ids:
        orders_query = orders_query.where(Order.id.in_(payload.order_ids))
    orders = db.scalars(orders_query.order_by(Order.due_time.asc().nulls_last())).all()
    review_orders = [order.order_no for order in orders if order.geocode_status == "needs_review"]
    if review_orders:
        raise HTTPException(
            status_code=400,
            detail="以下订单地址由兜底定位生成，需先人工复核坐标：" + "、".join(review_orders[:10]),
        )

    vehicles_query = select(Vehicle).where(Vehicle.status == "available")
    if payload.vehicle_ids:
        vehicles_query = vehicles_query.where(Vehicle.id.in_(payload.vehicle_ids))
    vehicles = [
        {
            "id": str(vehicle.id),
            "plate_no": vehicle.plate_no,
            "vehicle_type": vehicle.vehicle_type,
            "length_cm": float(vehicle.length_cm),
            "width_cm": float(vehicle.width_cm),
            "height_cm": float(vehicle.height_cm),
            "volume_m3": float(vehicle.volume_m3),
            "max_load_kg": float(vehicle.max_load_kg),
        }
        for vehicle in db.scalars(vehicles_query.order_by(Vehicle.plate_no)).all()
    ]
    box_types = db.scalars(select(BoxType).where(BoxType.enabled.is_(True))).all()
    validate_box_inventory_volume(orders, box_types)

    result = solve_vrptw(orders=orders, vehicles=vehicles, box_types=box_types)
    task = OptimizationTask(
        task_no=f"OPT-{uuid4().hex[:10].upper()}",
        name=payload.name,
        status="completed" if result.solutions else "failed",
        objective=payload.objective,
        order_count=len(orders),
        vehicle_count=len(vehicles),
        error_message=None if result.solutions else "没有可用订单或车辆",
    )
    db.add(task)
    db.flush()

    for index, solution in enumerate(result.solutions, start=1):
        db.add(
            OptimizationSolution(
                task_id=task.id,
                solution_no=index,
                solution_type=solution["solution_type"],
                is_selected=index == 1,
                total_cost=solution["total_cost"],
                total_distance_km=solution["total_distance_km"],
                total_carbon_kg=solution["total_carbon_kg"],
                avg_loss_rate=solution["avg_loss_rate"],
                on_time_rate=solution["on_time_rate"],
                total_tardiness_min=solution["total_tardiness_min"],
                vehicle_count=solution["vehicle_count"],
                payload=solution,
            )
        )

    if result.solutions:
        optimized_order_ids = {
            UUID(stop["order_id"])
            for route in result.solutions[0]["routes"]
            for stop in route["stops"]
        }
        for order in orders:
            if order.id in optimized_order_ids:
                order.status = "optimized"

    db.commit()
    db.refresh(task)
    return {"task": task, "status": result.status, "solutions": result.solutions}


@router.get("/history/compare")
def compare_recent_solutions(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher"))):
    rows = db.scalars(
        select(OptimizationSolution).order_by(OptimizationSolution.created_at.desc()).limit(20)
    ).all()
    return [
        {
            "task_id": str(row.task_id),
            "solution_no": row.solution_no,
            "solution_type": row.solution_type,
            "total_cost": float(row.total_cost),
            "total_distance_km": float(row.total_distance_km),
            "total_carbon_kg": float(row.total_carbon_kg),
            "on_time_rate": float(row.on_time_rate),
            "vehicle_count": row.vehicle_count,
            "is_selected": row.is_selected,
        }
        for row in rows
    ]


@router.get("/solutions/latest")
def latest_selected_solution(db: Session = Depends(get_db), _user=Depends(auth.require_roles("admin", "dispatcher", "warehouse", "driver"))):
    row = db.scalar(
        select(OptimizationSolution)
        .where(OptimizationSolution.is_selected.is_(True))
        .order_by(OptimizationSolution.created_at.desc())
        .limit(1)
    )
    if not row:
        return None
    return {
        "task_id": str(row.task_id),
        "solution_no": row.solution_no,
        "solution_type": row.solution_type,
        "created_at": row.created_at,
        "payload": row.payload,
    }


@router.get("/tasks/{task_id}/solutions", response_model=list[SolutionSummary])
def list_task_solutions(
    task_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(auth.require_roles("admin", "dispatcher", "warehouse", "driver")),
):
    rows = db.scalars(
        select(OptimizationSolution)
        .where(OptimizationSolution.task_id == task_id)
        .order_by(OptimizationSolution.solution_no)
    ).all()
    return [
        SolutionSummary(
            solution_type=row.solution_type,
            total_cost=float(row.total_cost),
            total_distance_km=float(row.total_distance_km),
            total_carbon_kg=float(row.total_carbon_kg),
            avg_loss_rate=float(row.avg_loss_rate),
            on_time_rate=float(row.on_time_rate),
            total_tardiness_min=float(row.total_tardiness_min),
            vehicle_count=row.vehicle_count,
            payload=row.payload,
        )
        for row in rows
    ]
