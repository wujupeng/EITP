"""SAL 发货与包装与退货表 - 发货单/发货行/包装记录/包装行/退货/退货行。

Revision ID: 041
Revises: 040
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sal_shipment_order (
            shipment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            shipment_code        VARCHAR(64) NOT NULL,
            order_ids            JSONB NOT NULL DEFAULT '[]'::jsonb,
            shipping_warehouse_id UUID NOT NULL,
            picking_strategy     VARCHAR(32) NOT NULL DEFAULT 'fifo',
            logistics_no         VARCHAR(128),
            carrier              VARCHAR(128),
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            wms_picking_task_id  UUID,
            wms_shipping_id      UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            idempotency_key      VARCHAR(128) NOT NULL DEFAULT '',
            correlation_id       UUID,
            created_by           UUID,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            shipped_at           TIMESTAMPTZ,
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_shipment_code UNIQUE (tenant_id, shipment_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_shipment_idempotency ON sal_shipment_order (tenant_id, idempotency_key)")
    op.execute("CREATE INDEX idx_sal_shipment_correlation ON sal_shipment_order (tenant_id, correlation_id)")
    op.execute("CREATE INDEX idx_sal_shipment_tenant_status ON sal_shipment_order (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_shipment_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            shipment_id          UUID NOT NULL REFERENCES sal_shipment_order(shipment_id),
            order_line_id        UUID NOT NULL,
            enterprise_sku_id    UUID NOT NULL,
            ship_quantity        NUMERIC(18,6) NOT NULL,
            wms_picking_detail_id UUID,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_sline_shipment ON sal_shipment_line (tenant_id, shipment_id)")

    op.execute("""
        CREATE TABLE sal_packing_record (
            packing_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            shipment_id          UUID NOT NULL REFERENCES sal_shipment_order(shipment_id),
            package_count        INTEGER NOT NULL DEFAULT 0,
            total_gross_weight   NUMERIC(18,4) NOT NULL DEFAULT 0,
            total_net_weight     NUMERIC(18,4) NOT NULL DEFAULT 0,
            total_volume         NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            packed_by            UUID,
            packed_at            TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_packing_shipment ON sal_packing_record (tenant_id, shipment_id)")

    op.execute("""
        CREATE TABLE sal_packing_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            packing_id           UUID NOT NULL REFERENCES sal_packing_record(packing_id),
            shipment_line_id     UUID NOT NULL,
            carton_no            VARCHAR(64) NOT NULL DEFAULT '',
            packed_quantity      NUMERIC(18,6) NOT NULL,
            gross_weight         NUMERIC(18,4) NOT NULL DEFAULT 0,
            net_weight           NUMERIC(18,4) NOT NULL DEFAULT 0,
            volume               NUMERIC(18,6) NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_pline_packing ON sal_packing_line (tenant_id, packing_id)")

    op.execute("""
        CREATE TABLE sal_sales_return (
            return_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            return_code          VARCHAR(64) NOT NULL,
            order_id             UUID NOT NULL REFERENCES sal_sales_order(order_id),
            original_shipment_id UUID NOT NULL,
            return_reason        VARCHAR(512) NOT NULL DEFAULT '',
            refund_amount        NUMERIC(18,6) NOT NULL DEFAULT 0,
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            wms_receiving_id     UUID,
            inv_transaction_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
            idempotency_key      VARCHAR(128) NOT NULL DEFAULT '',
            correlation_id       UUID,
            submitted_by         UUID,
            submitted_at         TIMESTAMPTZ,
            approved_by          UUID,
            approved_at          TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_return_code UNIQUE (tenant_id, return_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_return_idempotency ON sal_sales_return (tenant_id, idempotency_key)")
    op.execute("CREATE INDEX idx_sal_return_correlation ON sal_sales_return (tenant_id, correlation_id)")
    op.execute("CREATE INDEX idx_sal_return_order ON sal_sales_return (tenant_id, order_id)")
    op.execute("CREATE INDEX idx_sal_return_tenant_status ON sal_sales_return (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_return_line (
            line_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            return_id            UUID NOT NULL REFERENCES sal_sales_return(return_id),
            line_number          INTEGER NOT NULL DEFAULT 1,
            order_line_id        UUID NOT NULL,
            shipment_line_id     UUID,
            enterprise_sku_id    UUID NOT NULL,
            return_quantity      NUMERIC(18,6) NOT NULL,
            refund_amount        NUMERIC(18,6) NOT NULL DEFAULT 0,
            qc_result            VARCHAR(32) NOT NULL DEFAULT '',
            disposition          VARCHAR(32) NOT NULL DEFAULT '',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_rline_return ON sal_return_line (tenant_id, return_id)")


def downgrade() -> None:
    for tbl in [
        "sal_return_line", "sal_sales_return", "sal_packing_line",
        "sal_packing_record", "sal_shipment_line", "sal_shipment_order",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")