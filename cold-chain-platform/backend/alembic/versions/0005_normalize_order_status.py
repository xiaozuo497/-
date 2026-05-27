"""normalize order status values

Revision ID: 0005_normalize_order_status
Revises: 0004_dispatch_exceptions
Create Date: 2026-05-08
"""

from alembic import op


revision = "0005_normalize_order_status"
down_revision = "0004_dispatch_exceptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        update orders
        set status = case
            when status in ('pending', 'draft') then 'pending'
            when status in ('optimized', '已优化') or status like '%优化%' then 'optimized'
            when status in ('dispatched', '已派车') or status like '%派%' then 'dispatched'
            when status in ('in_transit', '运输中') or status like '%运输%' then 'in_transit'
            when status in ('delivered', '已送达') or status like '%送达%' then 'delivered'
            when status in ('exception', '异常') or status like '%异常%' then 'exception'
            else status
        end
        where status is not null
        """
    )


def downgrade() -> None:
    pass
