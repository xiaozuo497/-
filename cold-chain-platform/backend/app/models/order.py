from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    origin_name: Mapped[str] = mapped_column(String(128))
    destination_name: Mapped[str] = mapped_column(String(128))
    destination_address: Mapped[str | None] = mapped_column(Text)
    lng: Mapped[float | None] = mapped_column(Numeric(12, 8))
    lat: Mapped[float | None] = mapped_column(Numeric(12, 8))
    geocode_source: Mapped[str | None] = mapped_column(String(32))
    geocode_status: Mapped[str] = mapped_column(String(32), default="pending")
    box_type_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("box_types.id"))
    box_count: Mapped[int] = mapped_column(default=0)
    unit_weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), default=12.6)
    ready_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contact_name: Mapped[str | None] = mapped_column(String(64))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="draft")

    box_type = relationship("BoxType")


class DeliveryRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_records"

    order_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("vehicles.id"))
    actual_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="delivered")
    note: Mapped[str | None] = mapped_column(Text)

    order = relationship("Order")


class DispatchAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dispatch_assignments"

    optimization_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("optimization_tasks.id")
    )
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("vehicles.id"))
    route_sequence: Mapped[int] = mapped_column(default=0)
    planned_arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="dispatched")

    order = relationship("Order")


class OperationException(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operation_exceptions"

    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("orders.id"))
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("vehicles.id"))
    exception_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
    resolution: Mapped[str | None] = mapped_column(Text)
