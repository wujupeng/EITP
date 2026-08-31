"""WMS 作业单据表 - 收货/上架/拣货/移库/发货。

Revision ID: 033
Revises: 032
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 收货单 + 收货行 ---
    op.execute(
        "CREATE TABLE wms_receiving_order ("
        "    receiving_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    source_document_id     UUID NOT NULL,"
        "    source_document_type   VARCHAR(32) NOT NULL,"
        "    warehouse_id           UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    zone_id                UUID NOT NULL REFERENCES wms_zone(zone_id),"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'draft',"
        "    over_receive_ratio     NUMERIC(6,4) NOT NULL DEFAULT 0 CHECK (over_receive_ratio >= 0),"
        "    inv_transaction_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_recv_status CHECK (status IN ('draft','submitted','executing','completed'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_recv_tenant_status ON wms_receiving_order (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_recv_source_doc ON wms_receiving_order (tenant_id, source_document_id)")

    op.execute(
        "CREATE TABLE wms_receiving_line ("
        "    line_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    receiving_id           UUID NOT NULL REFERENCES wms_receiving_order(receiving_id),"
        "    sku_id                 UUID NOT NULL,"
        "    ordered_quantity       NUMERIC(18,6) NOT NULL CHECK (ordered_quantity >= 0),"
        "    received_quantity      NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (received_quantity >= 0),"
        "    location_id            UUID REFERENCES wms_location(location_id),"
        "    is_inspection_required BOOLEAN NOT NULL DEFAULT TRUE,"
        "    batch_lot              JSONB NOT NULL DEFAULT '{}'::jsonb,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_recv_line_order ON wms_receiving_line (tenant_id, receiving_id)")
    op.execute("CREATE INDEX idx_wms_recv_line_sku ON wms_receiving_line (tenant_id, sku_id)")

    # --- 上架任务 ---
    op.execute(
        "CREATE TABLE wms_putaway_task ("
        "    putaway_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    source_location_id     UUID NOT NULL REFERENCES wms_location(location_id),"
        "    target_location_id     UUID REFERENCES wms_location(location_id),"
        "    sku_id                 UUID NOT NULL,"
        "    quantity               NUMERIC(18,6) NOT NULL CHECK (quantity >= 0),"
        "    putaway_quantity       NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (putaway_quantity >= 0),"
        "    putaway_strategy       VARCHAR(32) NOT NULL DEFAULT 'manual',"
        "    source_document_id     UUID NOT NULL,"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'pending',"
        "    inv_transaction_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    completed_at           TIMESTAMPTZ,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_putaway_status CHECK (status IN ('pending','target_set','executing','completed','cancelled')),"
        "    CONSTRAINT chk_wms_putaway_strategy CHECK (putaway_strategy IN ('manual','nearest','empty_first','same_sku','same_product_concentrate','zoned','by_turnover'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_putaway_tenant_status ON wms_putaway_task (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_putaway_source_loc ON wms_putaway_task (tenant_id, source_location_id)")
    op.execute("CREATE INDEX idx_wms_putaway_sku ON wms_putaway_task (tenant_id, sku_id, status)")

    # --- 拣货任务 + 拣货行 ---
    op.execute(
        "CREATE TABLE wms_picking_task ("
        "    picking_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    source_order_id        UUID NOT NULL,"
        "    source_order_type      VARCHAR(32) NOT NULL,"
        "    warehouse_id           UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    picking_strategy       VARCHAR(16) NOT NULL DEFAULT 'fifo',"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'draft',"
        "    reservation_id         UUID,"
        "    inv_transaction_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_picking_status CHECK (status IN ('draft','reserved','executing','completed','cancelled')),"
        "    CONSTRAINT chk_wms_picking_strategy CHECK (picking_strategy IN ('fifo','lifo','fefo','manual','by_location','by_batch'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_picking_tenant_status ON wms_picking_task (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_picking_source_order ON wms_picking_task (tenant_id, source_order_id)")

    op.execute(
        "CREATE TABLE wms_picking_line ("
        "    line_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    picking_task_id        UUID NOT NULL REFERENCES wms_picking_task(picking_id),"
        "    sku_id                 UUID NOT NULL,"
        "    source_location_id     UUID NOT NULL REFERENCES wms_location(location_id),"
        "    required_quantity      NUMERIC(18,6) NOT NULL CHECK (required_quantity >= 0),"
        "    picked_quantity        NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (picked_quantity >= 0),"
        "    strategy               VARCHAR(16) NOT NULL DEFAULT 'fifo',"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_picking_line_task ON wms_picking_line (tenant_id, picking_task_id)")
    op.execute("CREATE INDEX idx_wms_picking_line_sku_loc ON wms_picking_line (tenant_id, sku_id, source_location_id)")

    # --- 移库单 + 移库行 ---
    op.execute(
        "CREATE TABLE wms_transfer_order ("
        "    transfer_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    warehouse_id           UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'draft',"
        "    require_approval       BOOLEAN NOT NULL DEFAULT FALSE,"
        "    approver_id            UUID,"
        "    approved_at            TIMESTAMPTZ,"
        "    approval_opinion       VARCHAR(512),"
        "    inv_transaction_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_transfer_status CHECK (status IN ('draft','submitted','approved','rejected','executing','completed','cancelled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_transfer_tenant_status ON wms_transfer_order (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_transfer_warehouse ON wms_transfer_order (tenant_id, warehouse_id, status)")

    op.execute(
        "CREATE TABLE wms_transfer_line ("
        "    line_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    transfer_order_id      UUID NOT NULL REFERENCES wms_transfer_order(transfer_id),"
        "    sku_id                 UUID NOT NULL,"
        "    source_location_id     UUID NOT NULL REFERENCES wms_location(location_id),"
        "    target_location_id     UUID NOT NULL REFERENCES wms_location(location_id),"
        "    quantity               NUMERIC(18,6) NOT NULL CHECK (quantity >= 0),"
        "    transferred_quantity   NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (transferred_quantity >= 0),"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_transfer_line_order ON wms_transfer_line (tenant_id, transfer_order_id)")
    op.execute("CREATE INDEX idx_wms_transfer_line_sku ON wms_transfer_line (tenant_id, sku_id)")

    # --- 发货单 + 发货行 ---
    op.execute(
        "CREATE TABLE wms_shipping_order ("
        "    shipping_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    source_order_id        UUID NOT NULL,"
        "    warehouse_id           UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    zone_id                UUID NOT NULL REFERENCES wms_zone(zone_id),"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'draft',"
        "    picking_completed      BOOLEAN NOT NULL DEFAULT FALSE,"
        "    logistics_no           VARCHAR(128),"
        "    logistics_company      VARCHAR(128),"
        "    shipped_at             TIMESTAMPTZ,"
        "    inv_transaction_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_shipping_status CHECK (status IN ('draft','executing','completed','cancelled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_shipping_tenant_status ON wms_shipping_order (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_shipping_source_order ON wms_shipping_order (tenant_id, source_order_id)")

    op.execute(
        "CREATE TABLE wms_shipping_line ("
        "    line_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    shipping_order_id      UUID NOT NULL REFERENCES wms_shipping_order(shipping_id),"
        "    sku_id                 UUID NOT NULL,"
        "    quantity               NUMERIC(18,6) NOT NULL CHECK (quantity >= 0),"
        "    logistics_no           VARCHAR(128),"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_shipping_line_order ON wms_shipping_line (tenant_id, shipping_order_id)")
    op.execute("CREATE INDEX idx_wms_shipping_line_sku ON wms_shipping_line (tenant_id, sku_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wms_shipping_line CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_shipping_order CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_transfer_line CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_transfer_order CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_picking_line CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_picking_task CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_putaway_task CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_receiving_line CASCADE")
    op.execute("DROP TABLE IF EXISTS wms_receiving_order CASCADE")