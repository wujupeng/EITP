"""PUR RLS 策略 + 红线防护 + 权限注册。

Revision ID: 037
Revises: 036
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


_PUR_TABLES = [
    "pur_supplier", "pur_supplier_scope", "pur_quotation", "pur_quotation_line",
    "pur_supplier_evaluation", "pur_purchase_request", "pur_purchase_request_line",
    "pur_purchase_order", "pur_purchase_order_line", "pur_asn", "pur_asn_line",
    "pur_purchase_receipt", "pur_purchase_receipt_line", "pur_purchase_return",
    "pur_purchase_return_line", "pur_purchase_settlement", "pur_invoice",
    "pur_payment_request", "pur_purchase_audit", "pur_reconcile_diff",
]


def upgrade() -> None:
    op.execute("DO $$ BEGIN CREATE ROLE pur_service_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    for tbl in _PUR_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl}
            FOR ALL
            TO public
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """)
        op.execute(f"CREATE POLICY rls_{tbl}_service ON {tbl} FOR SELECT TO pur_service_role USING (true)")

    op.execute("REVOKE INSERT, UPDATE, DELETE ON inv_inventory_ledger FROM pur_service_role")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON inv_inventory_balance FROM pur_service_role")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON wms_inventory_position FROM pur_service_role")

    op.execute("""
        INSERT INTO iam_permission (id, code, name, module, description)
        VALUES
            (gen_random_uuid(), 'pur:supplier:manage', '供应商管理', 'pur', '企业级 - 管理供应商档案/供货范围'),
            (gen_random_uuid(), 'pur:supplier:query', '查询供应商', 'pur', '企业级 - 查询供应商列表与详情'),
            (gen_random_uuid(), 'pur:quotation:manage', '报价单管理', 'pur', '企业级 - 管理供应商报价单'),
            (gen_random_uuid(), 'pur:evaluation:manage', '供应商评估', 'pur', '企业级 - 供应商绩效评估'),
            (gen_random_uuid(), 'pur:request:create', '创建采购申请', 'pur', '企业级 - 发起采购申请'),
            (gen_random_uuid(), 'pur:request:approve', '审批采购申请', 'pur', '企业级 - 审批采购申请'),
            (gen_random_uuid(), 'pur:request:query', '查询采购申请', 'pur', '企业级 - 查询采购申请列表'),
            (gen_random_uuid(), 'pur:order:create', '创建采购订单', 'pur', '企业级 - 创建采购订单'),
            (gen_random_uuid(), 'pur:order:approve', '审批采购订单', 'pur', '企业级 - 审批采购订单'),
            (gen_random_uuid(), 'pur:order:send', '发送采购订单', 'pur', '企业级 - 发送采购订单给供应商'),
            (gen_random_uuid(), 'pur:order:change', '变更采购订单', 'pur', '企业级 - 变更已审批采购订单'),
            (gen_random_uuid(), 'pur:order:cancel', '取消采购订单', 'pur', '企业级 - 取消采购订单'),
            (gen_random_uuid(), 'pur:order:close', '关闭采购订单', 'pur', '企业级 - 关闭已完成的采购订单'),
            (gen_random_uuid(), 'pur:order:query', '查询采购订单', 'pur', '企业级 - 查询采购订单列表与详情'),
            (gen_random_uuid(), 'pur:asn:manage', '管理到货通知', 'pur', '企业级 - 创建/管理ASN到货通知'),
            (gen_random_uuid(), 'pur:receipt:execute', '执行采购收货', 'pur', '企业级 - 确认采购到货收货'),
            (gen_random_uuid(), 'pur:receipt:query', '查询采购收货', 'pur', '企业级 - 查询采购收货记录'),
            (gen_random_uuid(), 'pur:return:create', '创建采购退货', 'pur', '企业级 - 发起采购退货申请'),
            (gen_random_uuid(), 'pur:return:approve', '审批采购退货', 'pur', '企业级 - 审批采购退货申请'),
            (gen_random_uuid(), 'pur:return:query', '查询采购退货', 'pur', '企业级 - 查询采购退货记录'),
            (gen_random_uuid(), 'pur:settlement:execute', '执行采购结算', 'pur', '企业级 - 执行采购对账与结算'),
            (gen_random_uuid(), 'pur:invoice:manage', '发票管理', 'pur', '企业级 - 管理采购发票与匹配'),
            (gen_random_uuid(), 'pur:payment:request', '付款申请', 'pur', '企业级 - 发起付款申请'),
            (gen_random_uuid(), 'pur:payment:confirm', '付款确认', 'pur', '企业级 - 确认付款完成'),
            (gen_random_uuid(), 'pur:reconcile:execute', '采购对账', 'pur', '企业级 - 执行采购WMS INV三边对账')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM iam_permission WHERE module = 'pur'")
    for tbl in _PUR_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_service ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")