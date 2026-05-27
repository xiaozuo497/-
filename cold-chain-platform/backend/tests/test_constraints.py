from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.optimization import validate_box_inventory_volume
from app.services.packing_solver import build_grid_packing_plan
from app.services.vrptw_solver import solve_vrptw


def test_packing_reports_overflow_without_overlapping_last_slot():
    items = build_grid_packing_plan(
        route_order=[
            {
                "order_id": "order-1",
                "customer_name": "A",
                "box_count": 3,
                "box_type": "LH-600-220",
                "box_length_cm": 60,
                "box_width_cm": 40,
                "box_height_cm": 22,
            }
        ],
        truck_length_cm=100,
        truck_width_cm=40,
        truck_height_cm=22,
        front_buffer_cm=0,
        rear_buffer_cm=0,
    )

    assert items["capacity_count"] == 1
    assert items["box_count"] == 1
    assert items["overflow_count"] == 2
    assert items["is_feasible"] is False


def test_box_inventory_checks_each_box_type_count():
    box_type_id = uuid4()
    orders = [SimpleNamespace(order_no="SO-1", box_type_id=box_type_id, box_count=5)]
    box_types = [
        SimpleNamespace(
            id=box_type_id,
            code="C",
            name="LH-600-220",
            stock_quantity=4,
            length_cm=60,
            width_cm=40,
            height_cm=22,
        )
    ]

    with pytest.raises(HTTPException) as exc:
        validate_box_inventory_volume(orders, box_types)

    assert exc.value.status_code == 400
    assert "库存不足" in exc.value.detail


def test_vrptw_marks_over_capacity_solution_infeasible():
    order = SimpleNamespace(
        id=uuid4(),
        order_no="SO-1",
        destination_name="A",
        destination_address="A",
        lat=32.31,
        lng=118.32,
        box_count=200,
        unit_weight_kg=20,
        box_type_id=None,
        ready_time=None,
        due_time=None,
    )
    vehicle = {
        "id": str(uuid4()),
        "plate_no": "TEST-1",
        "vehicle_type": "cold",
        "length_cm": 408,
        "width_cm": 210,
        "height_cm": 210,
        "volume_m3": 18.14,
        "max_load_kg": 1000,
    }

    result = solve_vrptw(orders=[order], vehicles=[vehicle], box_types=[])

    assert result.solutions
    assert result.solutions[0]["is_capacity_feasible"] is False
    assert result.status == "partial"
