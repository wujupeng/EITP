"""MDM INV Ledger Trigger 双保险整改。

在 INV-001 inv_inventory_ledger 的 REVOKE UPDATE/DELETE 基础上
增加 PostgreSQL Trigger 强制拒绝任何 UPDATE/DELETE 操作。

Revision ID: 026
Revises: 025
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE OR REPLACE FUNCTION fn_inv_ledger_append_only_guard() "
        "RETURNS trigger AS $$ "
        "BEGIN "
        "RAISE EXCEPTION 'EITP_INV_LEDGER_APPEND_ONLY: InventoryLedger is append-only, UPDATE/DELETE forbidden by trigger guard'; "
        "END; "
        "$$ LANGUAGE plpgsql;"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_inv_ledger_no_update ON inv_inventory_ledger;")
    op.execute(
        "CREATE TRIGGER trg_inv_ledger_no_update "
        "BEFORE UPDATE ON inv_inventory_ledger "
        "FOR EACH ROW EXECUTE FUNCTION fn_inv_ledger_append_only_guard();"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_inv_ledger_no_delete ON inv_inventory_ledger;")
    op.execute(
        "CREATE TRIGGER trg_inv_ledger_no_delete "
        "BEFORE DELETE ON inv_inventory_ledger "
        "FOR EACH ROW EXECUTE FUNCTION fn_inv_ledger_append_only_guard();"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_inv_audit_no_update ON inv_inventory_audit;")
    op.execute(
        "CREATE TRIGGER trg_inv_audit_no_update "
        "BEFORE UPDATE ON inv_inventory_audit "
        "FOR EACH ROW EXECUTE FUNCTION fn_inv_ledger_append_only_guard();"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_inv_audit_no_delete ON inv_inventory_audit;")
    op.execute(
        "CREATE TRIGGER trg_inv_audit_no_delete "
        "BEFORE DELETE ON inv_inventory_audit "
        "FOR EACH ROW EXECUTE FUNCTION fn_inv_ledger_append_only_guard();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_inv_ledger_no_update ON inv_inventory_ledger;")
    op.execute("DROP TRIGGER IF EXISTS trg_inv_ledger_no_delete ON inv_inventory_ledger;")
    op.execute("DROP TRIGGER IF EXISTS trg_inv_audit_no_update ON inv_inventory_audit;")
    op.execute("DROP TRIGGER IF EXISTS trg_inv_audit_no_delete ON inv_inventory_audit;")
    op.execute("DROP FUNCTION IF EXISTS fn_inv_ledger_append_only_guard();")
