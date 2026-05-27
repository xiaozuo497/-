def compute_vehicle_cost(
    *,
    distance_km: float,
    total_weight_kg: float,
    total_volume_m3: float,
    max_load_kg: float,
    vehicle_volume_m3: float,
    box_count: int,
    stop_count: int,
) -> dict[str, float]:
    """Cost model migrated from the prototype page."""
    volume_rate = total_volume_m3 / vehicle_volume_m3 if vehicle_volume_m3 else 0
    weight_rate = total_weight_kg / max_load_kg if max_load_kg else 0
    travel_hours = distance_km / 42
    refrigeration_energy = travel_hours * (4.8 + volume_rate * 1.6 + stop_count * 0.35)
    cost = (
        360
        + distance_km * (2.8 + weight_rate * 0.55)
        + refrigeration_energy * 1.15
        + box_count * 2.6
        + stop_count * 18
    )
    carbon = distance_km * (0.72 + weight_rate * 0.10) + refrigeration_energy * 0.45
    loss_rate = 0.052 + stop_count * 0.0015 + min(1, volume_rate) * 0.012
    return {
        "cost": round(cost, 2),
        "carbon_kg": round(carbon, 2),
        "loss_rate": round(loss_rate, 4),
        "refrigeration_energy": round(refrigeration_energy, 3),
    }

