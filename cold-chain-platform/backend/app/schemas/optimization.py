from uuid import UUID

from pydantic import BaseModel, Field


class OptimizationTaskCreate(BaseModel):
    name: str
    order_ids: list[UUID] = Field(min_length=1)
    vehicle_ids: list[UUID] = Field(min_length=1)
    objective: str = "on_time_min_cost"


class OptimizationTaskRead(BaseModel):
    id: UUID
    task_no: str
    name: str
    status: str
    objective: str
    order_count: int
    vehicle_count: int

    model_config = {"from_attributes": True}


class SolutionSummary(BaseModel):
    solution_type: str
    total_cost: float
    total_distance_km: float
    total_carbon_kg: float
    avg_loss_rate: float
    on_time_rate: float
    total_tardiness_min: float
    vehicle_count: int
    payload: dict

