"""PLT PostgreSQL 角色模型 - 建立 4 个统一角色。

Revision ID: 058
Revises: 057
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DO $$ BEGIN CREATE ROLE eitp_app_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE eitp_wms_service_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE eitp_readonly_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE eitp_platform_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    _BUSINESS_TABLES = [
        "mt_tenant", "mt_hierarchy", "mt_tenant_member", "mt_config",
        "iam_user", "iam_role", "iam_permission", "iam_session", "iam_token", "iam_data_scope",
        "inv_inventory_balance", "inv_inventory_ledger", "inv_inventory_reservation", "inv_inventory_document",
        "mdm_enterprise_product", "mdm_enterprise_sku", "mdm_barcode", "mdm_specification", "mdm_governance_workflow",
        "wms_space", "wms_location", "wms_receiving_order", "wms_picking_task", "wms_shipping_order", "wms_inventory_position",
        "pur_supplier", "pur_purchase_order", "pur_purchase_receipt", "pur_purchase_return", "pur_purchase_settlement",
        "sal_customer", "sal_sales_order", "sal_shipment_order", "sal_sales_return", "sal_sales_settlement", "sal_sales_invoice",
        "sec_certification_batch", "sec_certification_item", "sec_certification_report", "sec_certification_certificate", "sec_certification_config",
        "sec_certification_audit", "sec_platform_admin_access_request", "sec_platform_admin_access_log", "sec_redis_key_violation", "sec_evidence_snapshot",
    ]

    for tbl in _BUSINESS_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT, UPDATE ON {tbl} TO eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
        op.execute(f"DO $$ BEGIN GRANT SELECT ON {tbl} TO eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    _WMS_TABLES = ["wms_space", "wms_location", "wms_receiving_order", "wms_picking_task", "wms_shipping_order", "wms_inventory_position", "inv_inventory_balance", "inv_inventory_position"]
    for tbl in _WMS_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT, UPDATE ON {tbl} TO eitp_wms_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    _PLT_TABLES = [
        "plt_audit_record", "plt_audit_retention_policy", "plt_outbox_event", "plt_saga_instance", "plt_saga_step",
        "plt_idempotency_record", "plt_permission_matrix", "plt_menu_tree", "plt_permission_approval",
        "plt_tenant_quota", "plt_config_revision", "plt_job_definition", "plt_job_execution", "plt_job_schedule",
        "plt_api_version_contract", "plt_api_rate_limit_rule",
    ]
    for tbl in _PLT_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT ON {tbl} TO eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
        op.execute(f"DO $$ BEGIN GRANT SELECT ON {tbl} TO eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    op.execute("DO $$ BEGIN REVOKE UPDATE, DELETE ON plt_audit_record FROM eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE UPDATE, DELETE ON plt_audit_record FROM eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")


def downgrade() -> None:
    op.execute("DROP ROLE IF EXISTS eitp_app_role")
    op.execute("DROP ROLE IF EXISTS eitp_wms_service_role")
    op.execute("DROP ROLE IF EXISTS eitp_readonly_role")
    op.execute("DROP ROLE IF EXISTS eitp_platform_role")