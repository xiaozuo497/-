"""add dispatch assignments and operation exceptions

Revision ID: 0004_dispatch_exceptions
Revises: 0003_delivery_records
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_dispatch_exceptions"
down_revision = "0003_delivery_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_assignments",
        sa.Column("optimization_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_sequence", sa.Integer(), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["optimization_task_id"], ["optimization_tasks.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dispatch_assignments_order_id", "dispatch_assignments", ["order_id"])
    op.create_index("ix_dispatch_assignments_vehicle_id", "dispatch_assignments", ["vehicle_id"])

    op.create_table(
        "operation_exceptions",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exception_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("operation_exceptions")
    op.drop_index("ix_dispatch_assignments_vehicle_id", table_name="dispatch_assignments")
    op.drop_index("ix_dispatch_assignments_order_id", table_name="dispatch_assignments")
    op.drop_table("dispatch_assignments")
