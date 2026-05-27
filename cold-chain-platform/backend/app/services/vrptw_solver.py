from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from math import hypot

from app.services.packing_solver import build_grid_packing_plan


DEPOT = {
    "name": "滁州冷链中心",
    "lat": 32.3036,
    "lng": 118.3168,
}

ROUTE_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#22c55e"]
CUSTOMER_COLORS = [
    "#2563eb",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#06b6d4",
    "#84cc16",
    "#f97316",
    "#14b8a6",
    "#6366f1",
    "#a855f7",
]


@dataclass
class VrptwSolveResult:
    status: str
    solutions: list[dict]


def minutes_of(value: datetime | None, fallback: str) -> int:
    if value is None:
        hh, mm = fallback.split(":")
        return int(hh) * 60 + int(mm)
    local_time = value.time() if isinstance(value, datetime) else time(8, 0)
    return local_time.hour * 60 + local_time.minute


def minutes_label(total: int) -> str:
    total = max(0, int(round(total)))
    return f"{total // 60:02d}:{total % 60:02d}"


def distance_km(a: dict, b: dict) -> float:
    return hypot((float(a["lat"]) - float(b["lat"])) * 111, (float(a["lng"]) - float(b["lng"])) * 95) * 1.28


def order_to_stop(order, box_type_lookup: dict, index: int) -> dict:
    box_type = box_type_lookup.get(str(order.box_type_id), {"name": "LH-600-220", "code": "C", "length_cm": 60, "width_cm": 40, "height_cm": 22})
    return {
        "order_id": str(order.id),
        "order_no": order.order_no,
        "customer_name": order.destination_name,
        "address": order.destination_address or order.destination_name,
        "lat": float(order.lat or DEPOT["lat"]),
        "lng": float(order.lng or DEPOT["lng"]),
        "box_count": int(order.box_count),
        "unit_weight_kg": float(order.unit_weight_kg),
        "box_type": box_type["name"],
        "box_code": box_type["code"],
        "box_length_cm": float(box_type["length_cm"]),
        "box_width_cm": float(box_type["width_cm"]),
        "box_height_cm": float(box_type["height_cm"]),
        "ready_min": minutes_of(order.ready_time, "08:00"),
        "due_min": minutes_of(order.due_time, "18:00"),
        "ready_time": minutes_label(minutes_of(order.ready_time, "08:00")),
        "due_time": minutes_label(minutes_of(order.due_time, "18:00")),
        "color": CUSTOMER_COLORS[index % len(CUSTOMER_COLORS)],
    }


def evaluate_route(stops: list[dict], vehicle: dict, color: str) -> dict:
    current = DEPOT
    clock = 8 * 60
    route_distance = 0.0
    total_tardiness = 0
    stop_results = []
    late_started = False

    for index, stop in enumerate(stops):
        travel_min = max(8, int(distance_km(current, stop) / 42 * 60))
        if "_ortools_arrival_min" in stop:
            arrival = int(stop["_ortools_arrival_min"])
            clock = arrival
        else:
            clock += travel_min
            if clock < stop["ready_min"]:
                clock = stop["ready_min"]
            arrival = clock
        tardiness = max(0, arrival - stop["due_min"])
        total_tardiness += tardiness
        late_started = late_started or tardiness > 0
        segment_distance = distance_km(current, stop)
        route_distance += segment_distance
        stop_results.append(
            {
                **stop,
                "sequence": index + 1,
                "arrival_time": minutes_label(arrival),
                "tardiness_min": tardiness,
                "status": "迟到" if tardiness else "准时",
                "segment_distance_km": round(segment_distance, 2),
                "late_segment": late_started,
                "color": stop["color"],
            }
        )
        clock += 10
        current = stop

    route_distance += distance_km(current, DEPOT) if stops else 0
    box_count = sum(stop["box_count"] for stop in stops)
    total_weight = sum(stop["box_count"] * stop["unit_weight_kg"] for stop in stops)
    volume_m3 = sum(
        stop["box_count"] * stop["box_length_cm"] * stop["box_width_cm"] * stop["box_height_cm"] / 1_000_000
        for stop in stops
    )
    weight_rate = total_weight / max(float(vehicle["max_load_kg"]), 1)
    volume_rate = volume_m3 / max(float(vehicle["volume_m3"]), 1)
    capacity_violations = []
    if weight_rate > 1:
        capacity_violations.append(f"路线总重量 {total_weight:.1f} kg 超过车辆载重 {float(vehicle['max_load_kg']):.1f} kg")
    if volume_rate > 1:
        capacity_violations.append(f"路线总体积 {volume_m3:.2f} m3 超过车辆容积 {float(vehicle['volume_m3']):.2f} m3")
    load_rate = max(weight_rate, volume_rate)
    cooling_energy = route_distance / 42 * (4.8 + load_rate * 1.6 + len(stops) * 0.35)
    cost = 360 + route_distance * (2.8 + load_rate * 0.55) + cooling_energy * 1.15 + box_count * 2.6 + len(stops) * 18
    carbon = route_distance * (0.72 + load_rate * 0.10) + cooling_energy * 0.45

    packing = build_grid_packing_plan(
        route_order=stop_results,
        truck_length_cm=float(vehicle["length_cm"]),
        truck_width_cm=float(vehicle["width_cm"]),
        truck_height_cm=float(vehicle["height_cm"]),
    )
    constraint_violations = [*capacity_violations, *packing.get("violations", [])]
    packing_feasible = not constraint_violations

    return {
        "vehicle_id": vehicle["id"],
        "plate_no": vehicle["plate_no"],
        "vehicle_type": vehicle["vehicle_type"],
        "color": color,
        "stops": stop_results,
        "packing_order": list(reversed([stop["customer_name"] for stop in stop_results])),
        "distance_km": round(route_distance, 2),
        "cost": round(cost, 2),
        "carbon_kg": round(carbon, 2),
        "box_count": box_count,
        "total_weight_kg": round(total_weight, 2),
        "total_volume_m3": round(volume_m3, 3),
        "load_rate": round(min(load_rate, 1), 4),
        "raw_load_rate": round(load_rate, 4),
        "is_capacity_feasible": packing_feasible,
        "capacity_violations": capacity_violations,
        "packing_feasible": packing_feasible,
        "constraint_violations": constraint_violations,
        "on_time_rate": 1 if not stops else round(sum(1 for stop in stop_results if stop["tardiness_min"] == 0) / len(stops), 4),
        "total_tardiness_min": total_tardiness,
        "packing": packing,
    }


def assign_by_due_time(stops: list[dict], vehicles: list[dict]) -> list[list[dict]]:
    groups = [[] for _ in vehicles]
    sorted_stops = sorted(stops, key=lambda item: (item["due_min"], item["ready_min"], item["customer_name"]))
    for index, stop in enumerate(sorted_stops):
        groups[index % len(groups)].append(stop)
    return groups


def assign_by_capacity(stops: list[dict], vehicles: list[dict]) -> list[list[dict]]:
    groups = [[] for _ in vehicles]
    weights = [0.0 for _ in vehicles]
    volumes = [0.0 for _ in vehicles]
    for stop in sorted(stops, key=lambda item: item["box_count"] * item["unit_weight_kg"], reverse=True):
        stop_weight = stop["box_count"] * stop["unit_weight_kg"]
        stop_volume = stop["box_count"] * stop["box_length_cm"] * stop["box_width_cm"] * stop["box_height_cm"] / 1_000_000
        candidates = [
            idx
            for idx, vehicle in enumerate(vehicles)
            if weights[idx] + stop_weight <= float(vehicle["max_load_kg"])
            and volumes[idx] + stop_volume <= float(vehicle["volume_m3"])
        ]
        pool = candidates or list(range(len(vehicles)))
        index = min(
            pool,
            key=lambda idx: max(
                (weights[idx] + stop_weight) / max(float(vehicles[idx]["max_load_kg"]), 1),
                (volumes[idx] + stop_volume) / max(float(vehicles[idx]["volume_m3"]), 1),
            ),
        )
        groups[index].append(stop)
        weights[index] += stop_weight
        volumes[index] += stop_volume
    for group in groups:
        group.sort(key=lambda item: (item["due_min"], item["ready_min"]))
    return groups


def assign_single_route(stops: list[dict], vehicles: list[dict]) -> list[list[dict]]:
    groups = [[] for _ in vehicles]
    groups[0] = sorted(stops, key=lambda item: (item["due_min"], item["ready_min"], item["customer_name"]))
    return groups


def assign_by_nearest_neighbor(stops: list[dict], vehicles: list[dict]) -> list[list[dict]]:
    groups = [[] for _ in vehicles]
    remaining = sorted(stops, key=lambda item: (item["due_min"], item["ready_min"], item["customer_name"]))
    positions = [DEPOT for _ in vehicles]
    loads = [0 for _ in vehicles]

    while remaining:
        vehicle_index = min(range(len(vehicles)), key=lambda idx: loads[idx])
        current = positions[vehicle_index]
        stop = min(remaining, key=lambda item: (distance_km(current, item), item["due_min"], item["customer_name"]))
        groups[vehicle_index].append(stop)
        positions[vehicle_index] = stop
        loads[vehicle_index] += stop["box_count"]
        remaining.remove(stop)

    for group in groups:
        group.sort(key=lambda item: (item["due_min"], item["ready_min"]))
    return groups


def assign_by_region(stops: list[dict], vehicles: list[dict]) -> list[list[dict]]:
    groups = [[] for _ in vehicles]
    sorted_stops = sorted(stops, key=lambda item: (item["lng"], item["lat"], item["due_min"]))
    for index, stop in enumerate(sorted_stops):
        groups[index * len(vehicles) // max(1, len(sorted_stops))].append(stop)
    for group in groups:
        group.sort(key=lambda item: (item["due_min"], item["ready_min"]))
    return groups


def build_solution(*, solution_type: str, groups: list[list[dict]], vehicles: list[dict]) -> dict:
    routes = []
    for index, (vehicle, group) in enumerate(zip(vehicles, groups, strict=False)):
        if group:
            routes.append(evaluate_route(group, vehicle, ROUTE_COLORS[index % len(ROUTE_COLORS)]))

    total_orders = sum(len(route["stops"]) for route in routes)
    capacity_feasible = all(route["is_capacity_feasible"] for route in routes)
    on_time_orders = sum(sum(1 for stop in route["stops"] if stop["tardiness_min"] == 0) for route in routes)
    total_tardiness = sum(route["total_tardiness_min"] for route in routes)
    total_distance = sum(route["distance_km"] for route in routes)
    total_cost = sum(route["cost"] for route in routes)
    total_carbon = sum(route["carbon_kg"] for route in routes)
    infeasible_route_count = sum(1 for route in routes if not route["packing_feasible"])
    avg_loss_rate = min(0.12, 0.018 + total_distance / 10000)
    on_time_rate = 1 if total_orders == 0 else on_time_orders / total_orders

    return {
        "solution_type": solution_type,
        "is_feasible": on_time_rate >= 1 and capacity_feasible,
        "is_capacity_feasible": capacity_feasible,
        "packing_feasible": capacity_feasible,
        "infeasible_route_count": infeasible_route_count,
        "constraint_violations": [
            f"{route['plate_no']}: {message}"
            for route in routes
            for message in route["constraint_violations"]
        ],
        "routes": routes,
        "total_cost": round(total_cost, 2),
        "total_distance_km": round(total_distance, 2),
        "total_carbon_kg": round(total_carbon, 2),
        "avg_loss_rate": round(avg_loss_rate, 4),
        "on_time_rate": round(on_time_rate, 4),
        "total_tardiness_min": total_tardiness,
        "vehicle_count": len(routes),
    }


def solution_signature(solution: dict) -> tuple:
    return tuple(tuple(stop["order_id"] for stop in route["stops"]) for route in solution["routes"])


def stop_volume_m3(stop: dict) -> float:
    return stop["box_count"] * stop["box_length_cm"] * stop["box_width_cm"] * stop["box_height_cm"] / 1_000_000


def solve_vrptw(*, orders: list, vehicles: list[dict], box_types: list) -> VrptwSolveResult:
    if not orders or not vehicles:
        return VrptwSolveResult(status="failed", solutions=[])

    box_type_lookup = {
        str(box.id): {
            "name": box.name,
            "code": box.code,
            "length_cm": float(box.length_cm),
            "width_cm": float(box.width_cm),
            "height_cm": float(box.height_cm),
        }
        for box in box_types
    }
    stops = [order_to_stop(order, box_type_lookup, index) for index, order in enumerate(orders)]
    max_vehicle_count = max(1, min(len(vehicles), 6))
    vehicle_counts = list(range(1, max_vehicle_count + 1))
    raw_solutions = []

    for vehicle_count in vehicle_counts:
        selected_vehicles = vehicles[:vehicle_count]
        strategy_builders = [
            ("载重均衡", assign_by_capacity),
            ("时间窗优先", assign_by_due_time),
            ("邻近路线", assign_by_nearest_neighbor),
            ("区域分组", assign_by_region),
        ]
        if vehicle_count == 1:
            strategy_builders.insert(0, ("单车直送", assign_single_route))

        for strategy_name, assigner in strategy_builders:
            raw_solutions.append(
                build_solution(
                    solution_type=f"{strategy_name}方案 / {vehicle_count}辆车",
                    groups=assigner(stops, selected_vehicles),
                    vehicles=selected_vehicles,
                )
            )

    unique_solutions = []
    seen = set()
    for solution in raw_solutions:
        signature = solution_signature(solution)
        if signature in seen:
            continue
        seen.add(signature)
        unique_solutions.append(solution)

    unique_solutions.sort(
        key=lambda item: (
            not item["is_feasible"],
            not item["packing_feasible"],
            item["infeasible_route_count"],
            item["total_cost"],
            -item["on_time_rate"],
            item["total_tardiness_min"],
            item["vehicle_count"],
            item["total_distance_km"],
        )
    )

    if unique_solutions:
        unique_solutions[0]["solution_type"] = f"当前推荐可执行方案 / {unique_solutions[0]['vehicle_count']}辆车"

    status = "success" if any(solution["is_feasible"] for solution in unique_solutions) else "partial"
    return VrptwSolveResult(status=status, solutions=unique_solutions[:12])
