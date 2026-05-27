"""add box type stock quantity

Revision ID: 0002_box_type_stock_quantity
Revises: 0001_initial_schema
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_box_type_stock_quantity"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("box_types", sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE box_types SET stock_quantity = 200 WHERE stock_quantity = 0")
    op.alter_column("box_types", "stock_quantity", server_default=None)


def downgrade() -> None:
    op.drop_column("box_types", "stock_quantity")
