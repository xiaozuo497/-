from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrderBase(BaseModel):
    order_no: str
    origin_name: str = "滁州冷链中心"
    destination_name: str
    destination_address: str | None = None
    lng: float | None = None
    lat: float | None = None
    geocode_source: str | None = None
    geocode_status: str = "pending"
    box_type_id: UUID | None = None
    box_count: int = Field(ge=1)
    unit_weight_kg: float = Field(default=12.6, gt=0)
    ready_time: datetime | None = None
    due_time: datetime | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str = "draft"


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    destination_name: str | None = None
    destination_address: str | None = None
    lng: float | None = None
    lat: float | None = None
    geocode_status: str | None = None
    box_type_id: UUID | None = None
    box_count: int | None = Field(default=None, ge=1)
    unit_weight_kg: float | None = Field(default=None, gt=0)
    ready_time: datetime | None = None
    due_time: datetime | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str | None = None


class OrderRead(OrderBase):
    id: UUID
    box_type_code: str | None = None
    box_type_name: str | None = None

    model_config = {"from_attributes": True}


class DeliveryComplete(BaseModel):
    order_id: UUID
    vehicle_id: UUID | None = None
    actual_arrival: datetime | None = None
    note: str | None = None


class DeliveryRecordRead(BaseModel):
    id: UUID
    order_id: UUID
    vehicle_id: UUID | None = None
    actual_arrival: datetime
    status: str
    note: str | None = None

    model_config = {"from_attributes": True}


class DispatchCreate(BaseModel):
    task_id: UUID | None = None
    solution: dict


class DispatchAssignmentRead(BaseModel):
    id: UUID
    optimization_task_id: UUID | None = None
    order_id: UUID
    vehicle_id: UUID
    route_sequence: int
    planned_arrival: datetime | None = None
    status: str

    model_config = {"from_attributes": True}


class DispatchStatusUpdate(BaseModel):
    status: str


class OperationExceptionCreate(BaseModel):
    order_id: UUID | None = None
    vehicle_id: UUID | None = None
    exception_type: str
    description: str | None = None
    trigger_reoptimization: bool = False


class OperationExceptionRead(BaseModel):
    id: UUID
    order_id: UUID | None = None
    vehicle_id: UUID | None = None
    exception_type: str
    description: str | None = None
    status: str
    resolution: str | None = None

    model_config = {"from_attributes": True}
