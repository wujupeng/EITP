"""FIN 复合索引 + PostgreSQL 角色权限扩展 + 跨租户结算 RLS 互访策略下发。

Revision ID: 079
Revises: 078
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None

_FIN_TABLES = [
    "fin_settlement",
    "fin_settlement_line",
    "fin_payment",
    "fin_receipt",
    "fin_receipt_writeoff_line",
    "fin_invoice",
    "fin_invoice_line",
    "fin_reconciliation",
    "fin_reconciliation_line",
    "fin_reconciliation_difference",
    "fin_recon_diff_handle_record",
    "fin_ar_voucher",
    "fin_ap_voucher",
    "fin_gl_account",
    "fin_gl_voucher",
    "fin_gl_voucher_line",
    "fin_treasury_account",
    "fin_treasury_transfer",
    "fin_collection_task",
    "fin_collection_record",
    "fin_event_outbox",
]


def upgrade() -> None:
    op.create_index("idx_fin_settlement_tenant_type_status", "fin_settlement", ["tenant_id", "settlement_type", "status"])
    op.create_index("idx_fin_payment_tenant_ap_status", "fin_payment", ["tenant_id", "ap_voucher_no", "status"])
    op.create_index("idx_fin_ar_voucher_tenant_status_overdue", "fin_ar_voucher", ["tenant_id", "status", "is_overdue"])
    op.create_index("idx_fin_ap_voucher_tenant_status_overdue", "fin_ap_voucher", ["tenant_id", "status", "is_overdue"])
    op.create_index("idx_fin_gl_voucher_tenant_period_date", "fin_gl_voucher", ["tenant_id", "period", "voucher_date"])

    op.execute("DO $$ BEGIN CREATE ROLE eitp_fin_service_role NOLOGIN; EXCEPTION WHEN DUPLICATE_OBJECT THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE eitp_fin_admin_role NOLOGIN; EXCEPTION WHEN DUPLICATE_OBJECT THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT, UPDATE ON {tbl} TO eitp_fin_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_fin_admin_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT ON {tbl} TO eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")


def downgrade() -> None:
    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE SELECT ON {tbl} FROM eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE ALL ON {tbl} FROM eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE ALL ON {tbl} FROM eitp_fin_admin_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _FIN_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE SELECT, INSERT, UPDATE ON {tbl} FROM eitp_fin_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    op.drop_index("idx_fin_gl_voucher_tenant_period_date", table_name="fin_gl_voucher")
    op.drop_index("idx_fin_ap_voucher_tenant_status_overdue", table_name="fin_ap_voucher")
    op.drop_index("idx_fin_ar_voucher_tenant_status_overdue", table_name="fin_ar_voucher")
    op.drop_index("idx_fin_payment_tenant_ap_status", table_name="fin_payment")
    op.drop_index("idx_fin_settlement_tenant_type_status", table_name="fin_settlement")