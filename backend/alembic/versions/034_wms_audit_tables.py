"""WMS 审计与对账差异表 - append-only 审计 + WMS↔INV 对账差异。

Revision ID: 034
Revises: 033
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE wms_operation_audit ("
        "    audit_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    user_id                UUID NOT NULL,"
        "    event_type             VARCHAR(48) NOT NULL,"
        "    task_id                UUID,"
        "    sku_id                 UUID,"
        "    warehouse_id           UUID,"
        "    location_id            UUID,"
        "    before_state           JSONB,"
        "    after_state            JSONB,"
        "    inv_transaction_ids    JSONB,"
        "    reason                 VARCHAR(512),"
        "    operated_at            TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_audit_operated ON wms_operation_audit (tenant_id, operated_at)")
    op.execute("CREATE INDEX idx_wms_audit_task ON wms_operation_audit (tenant_id, task_id)")
    op.execute("CREATE INDEX idx_wms_audit_sku_loc ON wms_operation_audit (tenant_id, sku_id, location_id)")
    op.execute("CREATE INDEX idx_wms_audit_event ON wms_operation_audit (tenant_id, event_type, operated_at)")

    op.execute(
        "CREATE FUNCTION trg_wms_audit_no_update() RETURNS trigger AS $$"
        " BEGIN RAISE EXCEPTION 'wms_operation_audit is append-only: UPDATE prohibited';"
        " END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER trg_wms_audit_no_update BEFORE UPDATE ON wms_operation_audit"
        " FOR EACH ROW EXECUTE FUNCTION trg_wms_audit_no_update()"
    )
    op.execute(
        "CREATE FUNCTION trg_wms_audit_no_delete() RETURNS trigger AS $$"
        " BEGIN RAISE EXCEPTION 'wms_operation_audit is append-only: DELETE prohibited';"
        " END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER trg_wms_audit_no_delete BEFORE DELETE ON wms_operation_audit"
        " FOR EACH ROW EXECUTE FUNCTION trg_wms_audit_no_delete()"
    )

    op.execute(
        "CREATE TABLE wms_reconcile_diff ("
        "    diff_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    sku_id                 UUID NOT NULL,"
        "    warehouse_id           UUID NOT NULL REFERENCES wms_warehouse(warehouse_id),"
        "    location_id            UUID REFERENCES wms_location(location_id),"
        "    wms_quantity           NUMERIC(18,6) NOT NULL,"
        "    inv_quantity           NUMERIC(18,6) NOT NULL,"
        "    diff_quantity          NUMERIC(18,6) NOT NULL,"
        "    diff_type              VARCHAR(16) NOT NULL,"
        "    status                 VARCHAR(16) NOT NULL DEFAULT 'open',"
        "    resolved_at            TIMESTAMPTZ,"
        "    resolution_note        VARCHAR(512),"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_wms_reconcile_diff_type CHECK (diff_type IN ('wms_more','inv_more','match_mismatch')),"
        "    CONSTRAINT chk_wms_reconcile_status CHECK (status IN ('open','resolved','ignored'))"
        ")"
    )
    op.execute("CREATE INDEX idx_wms_reconcile_status ON wms_reconcile_diff (tenant_id, status)")
    op.execute("CREATE INDEX idx_wms_reconcile_sku_wh ON wms_reconcile_diff (tenant_id, sku_id, warehouse_id)")
    op.execute("CREATE INDEX idx_wms_reconcile_created ON wms_reconcile_diff (tenant_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS wms_reconcile_diff CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_wms_audit_no_delete ON wms_operation_audit")
    op.execute("DROP FUNCTION IF EXISTS trg_wms_audit_no_delete()")
    op.execute("DROP TRIGGER IF EXISTS trg_wms_audit_no_update ON wms_operation_audit")
    op.execute("DROP FUNCTION IF EXISTS trg_wms_audit_no_update()")
    op.execute("DROP TABLE IF EXISTS wms_operation_audit CASCADE")