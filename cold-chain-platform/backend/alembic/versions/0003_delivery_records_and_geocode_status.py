"""add delivery records and geocode status

Revision ID: 0003_delivery_records
Revises: 0002_box_type_stock_quantity
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_delivery_records"
down_revision = "0002_box_type_stock_quantity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("geocode_source", sa.String(length=32), nullable=True))
    op.add_column(
        "orders",
        sa.Column("geocode_status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.execute("UPDATE orders SET geocode_status = 'verified' WHERE lat IS NOT NULL AND lng IS NOT NULL")
    op.alter_column("orders", "geocode_status", server_default=None)

    op.create_table(
        "delivery_records",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_records_order_id", "delivery_records", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_records_order_id", table_name="delivery_records")
    op.drop_table("delivery_records")
    op.drop_column("orders", "geocode_status")
    op.drop_column("orders", "geocode_source")
