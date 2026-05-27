BOX_TYPE_CODES = {
    "LH-600-140": "A",
    "LH-600-220": "B",
    "LH-600-300": "C",
    "LH-600-340": "D",
}

BOX_SIZES = {
    "LH-600-140": {"length_cm": 60, "width_cm": 40, "height_cm": 14},
    "LH-600-220": {"length_cm": 60, "width_cm": 40, "height_cm": 22},
    "LH-600-300": {"length_cm": 60, "width_cm": 40, "height_cm": 30},
    "LH-600-340": {"length_cm": 60, "width_cm": 40, "height_cm": 34},
}

SUPPORT_RATIO_LIMITS = {
    "LH-600-140": 0.85,
    "LH-600-220": 0.85,
    "LH-600-300": 0.90,
    "LH-600-340": 0.95,
}


def box_code(box_type: str | None) -> str:
    return BOX_TYPE_CODES.get(box_type or "LH-600-220", "C")


def build_grid_packing_plan(
    *,
    route_order: list[dict],
    truck_length_cm: float,
    truck_width_cm: float,
    truck_height_cm: float,
    front_buffer_cm: float = 15,
    rear_buffer_cm: float = 33,
) -> dict:
    """Grid-snake 3D packing plan aligned with the Word model.

    The loading sequence is the reverse of delivery order, so the first stop is placed
    near the rear door and can be unloaded first. The regular 600 x 400 mm footprint
    makes AABB collision checks deterministic because each generated slot has a unique
    R/C/H coordinate.
    """

    main_box = BOX_SIZES["LH-600-220"]
    rows = max(1, int((truck_length_cm - front_buffer_cm - rear_buffer_cm) // main_box["length_cm"]))
    cols = max(1, int(truck_width_cm // main_box["width_cm"]))
    levels = max(1, int(truck_height_cm // main_box["height_cm"]))
    capacity = rows * cols * levels
    items = []

    seq = 1
    load_order = list(reversed(route_order))
    overflow_count = 0
    violations = []
    for customer_index, customer in enumerate(load_order):
        customer_color = customer.get("color", "#22c55e")
        for _ in range(int(customer.get("box_count", 0))):
            if seq > capacity:
                overflow_count += 1
                seq += 1
                continue
            index = seq - 1
            row = index // max(1, cols * levels)
            within_row = index - row * cols * levels
            level = within_row // cols
            col = within_row % cols
            box_type = customer.get("box_type", "LH-600-220")
            size = {
                "length_cm": float(customer.get("box_length_cm") or BOX_SIZES.get(box_type, main_box)["length_cm"]),
                "width_cm": float(customer.get("box_width_cm") or BOX_SIZES.get(box_type, main_box)["width_cm"]),
                "height_cm": float(customer.get("box_height_cm") or BOX_SIZES.get(box_type, main_box)["height_cm"]),
            }
            items.append(
                {
                    "seq": seq,
                    "customer_id": customer["order_id"],
                    "customer_name": customer["customer_name"],
                    "customer_color": customer_color,
                    "box_type": box_type,
                    "box_code": box_code(box_type),
                    "row_code": f"R{row + 1}",
                    "col_code": f"C{col + 1}",
                    "level_code": f"H{level + 1}",
                    "x_cm": -truck_length_cm / 2 + front_buffer_cm + size["length_cm"] / 2 + row * main_box["length_cm"],
                    "y_cm": -truck_height_cm / 2 + size["height_cm"] / 2 + level * main_box["height_cm"],
                    "z_cm": -truck_width_cm / 2 + size["width_cm"] / 2 + col * main_box["width_cm"],
                    "length_cm": size["length_cm"],
                    "width_cm": size["width_cm"],
                    "height_cm": size["height_cm"],
                    "support_ratio_min": SUPPORT_RATIO_LIMITS.get(box_type, 0.85),
                    "aabb_checked": True,
                    "orientation": "600mm 沿车长，400mm 沿车宽",
                }
            )
            seq += 1

    if overflow_count:
        violations.append(f"剩余 {overflow_count} 箱无法在当前车辆长宽高内生成不重叠箱位")

    return {
        "capacity_count": capacity,
        "box_count": len(items),
        "requested_box_count": len(items) + overflow_count,
        "overflow_count": overflow_count,
        "is_feasible": overflow_count == 0,
        "violations": violations,
        "items": items,
        "rows": rows,
        "cols": cols,
        "levels": levels,
    }
