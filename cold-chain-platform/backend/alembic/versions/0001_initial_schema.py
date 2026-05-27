"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("real_name", sa.String(length=64), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "box_types",
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("length_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("width_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("height_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("inner_size", sa.String(length=64), nullable=True),
        sa.Column("folded_size", sa.String(length=64), nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("capacity_desc", sa.String(length=128), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "optimization_tasks",
        sa.Column("task_no", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.String(length=64), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("vehicle_count", sa.Integer(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_optimization_tasks_task_no"), "optimization_tasks", ["task_no"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("plate_no", sa.String(length=32), nullable=False),
        sa.Column("vehicle_type", sa.String(length=64), nullable=False),
        sa.Column("length_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("width_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("height_cm", sa.Numeric(10, 2), nullable=False),
        sa.Column("volume_m3", sa.Numeric(10, 3), nullable=False),
        sa.Column("max_load_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("temperature_zone", sa.String(length=32), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicles_plate_no"), "vehicles", ["plate_no"], unique=True)

    op.create_table(
        "orders",
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("origin_name", sa.String(length=128), nullable=False),
        sa.Column("destination_name", sa.String(length=128), nullable=False),
        sa.Column("destination_address", sa.Text(), nullable=True),
        sa.Column("lng", sa.Numeric(12, 8), nullable=True),
        sa.Column("lat", sa.Numeric(12, 8), nullable=True),
        sa.Column("box_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("box_count", sa.Integer(), nullable=False),
        sa.Column("unit_weight_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("ready_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_name", sa.String(length=64), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["box_type_id"], ["box_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_order_no"), "orders", ["order_no"], unique=True)

    op.create_table(
        "optimization_solutions",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solution_no", sa.Integer(), nullable=False),
        sa.Column("solution_type", sa.String(length=64), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_distance_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_carbon_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("avg_loss_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("on_time_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("total_tardiness_min", sa.Numeric(12, 2), nullable=False),
        sa.Column("vehicle_count", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["optimization_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "packing_plans",
        sa.Column("solution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("box_count", sa.Integer(), nullable=False),
        sa.Column("capacity_count", sa.Integer(), nullable=False),
        sa.Column("volume_utilization", sa.Numeric(8, 4), nullable=False),
        sa.Column("weight_utilization", sa.Numeric(8, 4), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["solution_id"], ["optimization_solutions.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("packing_plans")
    op.drop_table("optimization_solutions")
    op.drop_index(op.f("ix_orders_order_no"), table_name="orders")
    op.drop_table("orders")
    op.drop_index(op.f("ix_vehicles_plate_no"), table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index(op.f("ix_optimization_tasks_task_no"), table_name="optimization_tasks")
    op.drop_table("optimization_tasks")
    op.drop_table("box_types")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")

