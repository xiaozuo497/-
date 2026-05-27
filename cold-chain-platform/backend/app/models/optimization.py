import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class OptimizationTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "optimization_tasks"

    task_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    objective: Mapped[str] = mapped_column(String(64), default="on_time_min_cost")
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class OptimizationSolution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "optimization_solutions"

    task_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("optimization_tasks.id"))
    solution_no: Mapped[int] = mapped_column(Integer)
    solution_type: Mapped[str] = mapped_column(String(64))
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    total_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_distance_km: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_carbon_kg: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    avg_loss_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    on_time_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    total_tardiness_min: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class PackingPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "packing_plans"

    solution_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("optimization_solutions.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("vehicles.id"))
    box_count: Mapped[int] = mapped_column(Integer, default=0)
    capacity_count: Mapped[int] = mapped_column(Integer, default=0)
    volume_utilization: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    weight_utilization: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    items: Mapped[list] = mapped_column(JSON, default=list)
