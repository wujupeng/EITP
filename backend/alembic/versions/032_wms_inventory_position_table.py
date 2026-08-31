"""WMS Inventory Position 表 - 物理库存分布面（含 batch/lot/serial/expiry P1 预留字段）。

Revision ID: 032
Revises: 031
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE wms_inventory_position ("
        "    position_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id             UUID NOT NULL,"
        "    sku_id                UUID NOT NULL,"
        "    warehouse_id          UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    location_id           UUID NOT NULL REFERENCES wms_location(location_id),"
        "    bin_id                UUID REFERENCES wms_bin(bin_id),"
        "    lot_number            VARCHAR(64),"
        "    batch_number          VARCHAR(64),"
        "    serial_number         VARCHAR(128),"
        "    expiry_date           DATE,"
        "    quantity              NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (quantity >= 0),"
        "    inventory_status      VARCHAR(16) NOT NULL DEFAULT 'available',"
        "    received_at           TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    last_updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_position_status CHECK (inventory_status IN ('available','in_qc','blocked','in_transit','quarantined','returned'))"
        ")"
    )
    op.execute(
        "CREATE UNIQUE INDEX uk_wms_position_compound ON wms_inventory_position "
        "(tenant_id, sku_id, location_id, COALESCE(lot_number, ''), COALESCE(batch_number, ''), COALESCE(serial_number, ''), inventory_status)"
    )
    op.execute("CREATE INDEX idx_wms_position_sku_wh ON wms_inventory_position (tenant_id, sku_id, warehouse_id)")
    op.execute("CREATE INDEX idx_wms_position_location ON wms_inventory_position (tenant_id, location_id)")
    op.execute("CREATE INDEX idx_wms_position_sku_status ON wms_inventory_position (tenant_id, sku_id, inventory_status)")
    op.execute("CREATE INDEX idx_wms_position_expiry ON wms_inventory_position (tenant_id, expiry_date) WHERE expiry_date IS NOT NULL")
    op.execute("CREATE INDEX idx_wms_position_reconcile ON wms_inventory_position (tenant_id, sku_id, warehouse_id, inventory_status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wms_inventory_position CASCADE")