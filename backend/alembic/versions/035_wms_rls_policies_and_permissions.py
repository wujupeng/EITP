"""WMS RLS 策略统一下发 + 20 个 WMS 操作权限注册 + 第一条红线数据库层防护。

Revision ID: 035
Revises: 034
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


_RLS_TABLES = [
    "wms_warehouse",
    "wms_zone",
    "wms_area",
    "wms_location",
    "wms_bin",
    "wms_equipment",
    "wms_task",
    "wms_task_line",
    "wms_inventory_position",
    "wms_receiving_order",
    "wms_receiving_line",
    "wms_putaway_task",
    "wms_picking_task",
    "wms_picking_line",
    "wms_transfer_order",
    "wms_transfer_line",
    "wms_shipping_order",
    "wms_shipping_line",
    "wms_operation_audit",
    "wms_reconcile_diff",
]

_WMS_PERMISSIONS = [
    ("wms:space:manage", "管理仓储空间", "wms"),
    ("wms:space:query", "查询仓储空间", "wms"),
    ("wms:position:query", "查询库存位置", "wms"),
    ("wms:task:manage", "管理WMS任务", "wms"),
    ("wms:task:assign", "分配WMS任务", "wms"),
    ("wms:task:claim", "领取WMS任务", "wms"),
    ("wms:task:cancel", "取消WMS任务", "wms"),
    ("wms:task:query", "查询WMS任务", "wms"),
    ("wms:receiving:execute", "执行收货作业", "wms"),
    ("wms:receiving:query", "查询收货作业", "wms"),
    ("wms:putaway:execute", "执行上架作业", "wms"),
    ("wms:putaway:query", "查询上架作业", "wms"),
    ("wms:picking:execute", "执行拣货作业", "wms"),
    ("wms:picking:query", "查询拣货作业", "wms"),
    ("wms:transfer:execute", "执行移库作业", "wms"),
    ("wms:transfer:approve", "审批移库申请", "wms"),
    ("wms:transfer:query", "查询移库作业", "wms"),
    ("wms:shipping:execute", "执行发货作业", "wms"),
    ("wms:shipping:query", "查询发货作业", "wms"),
    ("wms:reconcile:execute", "执行对账作业", "wms"),
]

_INV_TABLES_RED_LINE = [
    "inv_inventory_ledger",
    "inv_inventory_balance",
    "inv_inventory_reservation",
]


def upgrade() -> None:
    op.execute("DO $$ BEGIN CREATE ROLE wms_service_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY rls_{table}_tenant ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)"
        )

    for code, name, module in _WMS_PERMISSIONS:
        op.execute(
            f"INSERT INTO iam_permission (id, code, name, module, description) "
            f"VALUES (gen_random_uuid(), '{code}', '{name}', '{module}', '{name}') "
            f"ON CONFLICT (code) DO NOTHING"
        )

    for table in _INV_TABLES_RED_LINE:
        op.execute(f"REVOKE INSERT, UPDATE, DELETE ON {table} FROM wms_service_role")
        op.execute(f"GRANT SELECT ON {table} TO wms_service_role")


def downgrade() -> None:
    for table in _INV_TABLES_RED_LINE:
        op.execute(f"GRANT INSERT, UPDATE, DELETE ON {table} TO wms_service_role")

    for code, _, _ in _WMS_PERMISSIONS:
        op.execute(f"DELETE FROM iam_permission WHERE code = '{code}'")

    for table in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")