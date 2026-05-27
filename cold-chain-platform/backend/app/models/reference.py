import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32), default="dispatcher")
    status: Mapped[str] = mapped_column(String(24), default="active")


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    plate_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(64))
    length_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    width_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    height_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    volume_m3: Mapped[float] = mapped_column(Numeric(10, 3))
    max_load_kg: Mapped[float] = mapped_column(Numeric(10, 2))
    temperature_zone: Mapped[str] = mapped_column(String(32), default="冷藏")
    driver_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), default="available")

    driver = relationship("User")


class BoxType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "box_types"

    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    length_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    width_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    height_cm: Mapped[float] = mapped_column(Numeric(10, 2))
    inner_size: Mapped[str | None] = mapped_column(String(64))
    folded_size: Mapped[str | None] = mapped_column(String(64))
    gross_weight_kg: Mapped[float] = mapped_column(Numeric(10, 2))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    capacity_desc: Mapped[str | None] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
