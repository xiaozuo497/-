from uuid import UUID

from pydantic import BaseModel, Field


class VehicleRead(BaseModel):
    id: UUID
    plate_no: str
    vehicle_type: str
    length_cm: float
    width_cm: float
    height_cm: float
    volume_m3: float
    max_load_kg: float
    temperature_zone: str
    status: str

    model_config = {"from_attributes": True}


class VehicleCreate(BaseModel):
    plate_no: str
    vehicle_type: str = "冷藏车"
    length_cm: float = Field(gt=0)
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    volume_m3: float = Field(gt=0)
    max_load_kg: float = Field(gt=0)
    temperature_zone: str = "冷藏"
    status: str = "available"


class VehicleStatusUpdate(BaseModel):
    status: str


class BoxTypeRead(BaseModel):
    id: UUID
    code: str
    name: str
    length_cm: float
    width_cm: float
    height_cm: float
    gross_weight_kg: float
    stock_quantity: int
    enabled: bool

    model_config = {"from_attributes": True}


class BoxTypeUpsert(BaseModel):
    code: str
    name: str
    length_cm: float = Field(gt=0)
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    gross_weight_kg: float = Field(gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    inner_size: str | None = None
    folded_size: str | None = None
    capacity_desc: str | None = None
    enabled: bool = True


class BoxTypeStockUpdate(BaseModel):
    stock_quantity: int = Field(ge=0)


class ImportResult(BaseModel):
    ok: bool = True
    upserted: int
