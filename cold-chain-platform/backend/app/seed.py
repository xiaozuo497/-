import argparse
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.order import Order
from app.models.reference import BoxType, User, Vehicle
from app.services.geocode_service import geocode_destination

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def ensure_user(
    db,
    *,
    username: str,
    password: str,
    real_name: str,
    role: str,
    phone: str | None = None,
) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        user = User(username=username)
        db.add(user)
    user.password_hash = pwd_context.hash(password)
    user.real_name = real_name
    user.role = role
    user.phone = phone
    user.status = "active"
    db.flush()
    return user


def seed_box_types(db) -> None:
    items = [
        ("A", "LH-600-140", 60, 40, 14, "565x360x120mm", "600x400x55mm", 7.0, "尾货补充 / 软质单层低压装载"),
        ("B", "LH-600-220", 60, 40, 22, "565x365x210mm", "600x400x55mm", 12.6, "主力周转箱，适合多层装载"),
        ("C", "LH-600-300", 60, 40, 30, "560x355x285mm", "600x400x65mm", 13.0, "硬度较高货品 / 短途谨慎使用"),
        ("D", "LH-600-340", 60, 40, 34, "560x365x325mm", "600x400x65mm", 13.5, "小果径或低压损风险订单"),
    ]
    for code, name, length, width, height, inner, folded, weight, desc in items:
        box_type = db.scalar(select(BoxType).where(BoxType.code == code))
        if not box_type:
            box_type = BoxType(code=code)
            db.add(box_type)
        box_type.name = name
        box_type.length_cm = length
        box_type.width_cm = width
        box_type.height_cm = height
        box_type.inner_size = inner
        box_type.folded_size = folded
        box_type.gross_weight_kg = weight
        box_type.capacity_desc = desc
        box_type.enabled = True
    db.flush()


def seed_vehicles(db, driver: User) -> None:
    vehicles = [
        ("皖M-L001", "BJ5045XLCPHEV2 插电式混合动力冷藏车"),
        ("皖M-L002", "BJ5045XLCPHEV2 插电式混合动力冷藏车"),
        ("皖M-L003", "BJ5045XLCPHEV2 插电式混合动力冷藏车"),
        ("皖M-L004", "BJ5045XLCPHEV2 插电式混合动力冷藏车"),
    ]
    for plate_no, vehicle_type in vehicles:
        vehicle = db.scalar(select(Vehicle).where(Vehicle.plate_no == plate_no))
        if not vehicle:
            vehicle = Vehicle(plate_no=plate_no)
            db.add(vehicle)
        vehicle.vehicle_type = vehicle_type
        vehicle.length_cm = 408
        vehicle.width_cm = 210
        vehicle.height_cm = 210
        vehicle.volume_m3 = 18.14
        vehicle.max_load_kg = 3380
        vehicle.temperature_zone = "冷藏"
        vehicle.driver_id = driver.id
        vehicle.status = "available"


def seed_orders(db) -> int:
    boxes = db.scalars(select(BoxType)).all()
    box_by_name = {box.name: box for box in boxes}
    box_by_code = {box.code: box for box in boxes}
    base_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = [
        ("SO-20260504-001", "明光路生鲜点", "滁州市琅琊区明光路生鲜点", "LH-600-220", 24, "08:30", "10:30", "张店长", "13800010001"),
        ("SO-20260504-002", "清流路商超", "滁州市南谯区清流路商超", "LH-600-220", 28, "08:30", "10:40", "王经理", "13800010002"),
        ("SO-20260504-003", "凤凰路门店", "滁州市琅琊区凤凰路门店", "LH-600-220", 18, "09:00", "11:00", "李店长", "13800010003"),
        ("SO-20260504-004", "会峰路门店", "滁州市南谯区会峰路门店", "LH-600-300", 22, "09:20", "11:20", "赵经理", "13800010004"),
        ("SO-20260504-005", "丰乐大道门店", "滁州市琅琊区丰乐大道门店", "LH-600-140", 15, "09:30", "11:30", "刘店长", "13800010005"),
        ("SO-20260504-006", "琅琊区菜市场", "滁州市琅琊区菜市场", "LH-600-340", 20, "10:00", "12:00", "陈经理", "13800010006"),
        ("SO-20260504-007", "腰铺镇配送点", "滁州市南谯区腰铺镇配送点", "LH-600-220", 26, "10:00", "12:30", "周站长", "13800010007"),
        ("SO-20260504-008", "城南农贸点", "滁州市南谯区城南农贸点", "LH-600-300", 17, "10:30", "13:00", "孙店长", "13800010008"),
    ]

    def at(label: str) -> datetime:
        hour, minute = [int(part) for part in label.split(":")]
        return base_day + timedelta(hours=hour, minutes=minute)

    changed = 0
    for order_no, dest, address, box_name, count, ready, due, contact, phone in rows:
        order = db.scalar(select(Order).where(Order.order_no == order_no))
        if not order:
            order = Order(order_no=order_no)
            db.add(order)
            changed += 1
        else:
            continue
        point = geocode_destination(dest, address)
        order.origin_name = "滁州冷链中心"
        order.destination_name = dest
        order.destination_address = address
        order.lng = point["lng"]
        order.lat = point["lat"]
        box_type = box_by_name.get(box_name) or box_by_code.get(box_name)
        if not box_type:
            raise RuntimeError(f"未找到周转箱型号：{box_name}")
        order.box_type_id = box_type.id
        order.box_count = count
        order.unit_weight_kg = float(box_type.gross_weight_kg)
        order.ready_time = at(ready)
        order.due_time = at(due)
        order.contact_name = contact
        order.contact_phone = phone
        order.status = "待调度"
    return changed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed reference data for the cold-chain platform.")
    parser.add_argument(
        "--demo-orders",
        action="store_true",
        help="Create missing demo orders. Existing orders are never overwritten.",
    )
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        admin = ensure_user(db, username="admin", password="admin123", real_name="系统管理员", role="admin")
        ensure_user(db, username="dispatcher", password="dispatch123", real_name="调度员", role="dispatcher")
        ensure_user(db, username="warehouse", password="warehouse123", real_name="仓库员", role="warehouse")
        driver = ensure_user(db, username="driver", password="driver123", real_name="司机", role="driver")
        seed_box_types(db)
        seed_vehicles(db, driver)
        if args.demo_orders:
            created = seed_orders(db)
            print(f"Demo orders created: {created}")
        db.commit()
        print(f"Seed data ready. Default admin: {admin.username} / admin123")


if __name__ == "__main__":
    main()
