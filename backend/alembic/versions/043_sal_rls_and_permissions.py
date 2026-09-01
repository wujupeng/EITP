"""SAL RLS 策略 + 红线防护 + 权限注册 + 审计 append-only 防护。

Revision ID: 043
Revises: 042
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


_SAL_TABLES = [
    "sal_customer", "sal_customer_address", "sal_customer_contact",
    "sal_customer_category", "sal_credit_limit", "sal_customer_pricing",
    "sal_sales_quotation", "sal_sales_quotation_line",
    "sal_sales_order", "sal_sales_order_line",
    "sal_shipment_order", "sal_shipment_line", "sal_packing_record", "sal_packing_line",
    "sal_sales_return", "sal_return_line",
    "sal_sales_settlement", "sal_settlement_reconcile_line",
    "sal_sales_invoice", "sal_invoice_line", "sal_payment_receipt",
    "sal_sales_audit",
]


def upgrade() -> None:
    # ── 1. 创建 SAL 服务账号角色 ──
    op.execute("DO $$ BEGIN CREATE ROLE sal_service_role NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # ── 2. 所有 sal_* 表启用 RLS + 租户隔离策略 ──
    for tbl in _SAL_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY rls_{tbl}_tenant ON {tbl}
            FOR ALL
            TO public
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """)
        op.execute(f"CREATE POLICY rls_{tbl}_service ON {tbl} FOR SELECT TO sal_service_role USING (true)")

    # ── 3. 第一条红线防护：SAL 服务账号对 inv_*/wms_inventory_position 无直接写权限 ──
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON inv_inventory_ledger FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON inv_inventory_balance FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON inv_inventory_reservation FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON wms_inventory_position FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    # ── 4. 第二条红线防护：SAL 服务账号对收入账本表无直接写权限（如存在） ──
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON inv_revenue_ledger FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE INSERT, UPDATE, DELETE ON inv_receivable_ledger FROM sal_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    # ── 5. 审计表 append-only 防护：REVOKE UPDATE/DELETE + Trigger 双保险 ──
    op.execute("REVOKE UPDATE, DELETE ON sal_sales_audit FROM public")
    op.execute("REVOKE UPDATE, DELETE ON sal_sales_audit FROM sal_service_role")
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_sal_audit_no_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'sal_sales_audit is append-only: UPDATE not allowed';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_sal_audit_no_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'sal_sales_audit is append-only: DELETE not allowed';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER sal_audit_no_update BEFORE UPDATE ON sal_sales_audit FOR EACH ROW EXECUTE FUNCTION trg_sal_audit_no_update()")
    op.execute("CREATE TRIGGER sal_audit_no_delete BEFORE DELETE ON sal_sales_audit FOR EACH ROW EXECUTE FUNCTION trg_sal_audit_no_delete()")

    # ── 6. SAL 权限注入 iam_permission（~28 个 sal:* 权限） ──
    op.execute("""
        INSERT INTO iam_permission (id, code, name, module, description)
        VALUES
            (gen_random_uuid(), 'sal:customer:manage', '客户管理', 'sal', '企业级 - 管理客户档案/地址/联系人'),
            (gen_random_uuid(), 'sal:customer:query', '查询客户', 'sal', '企业级 - 查询客户列表与详情'),
            (gen_random_uuid(), 'sal:customer:approve', '审批客户', 'sal', '企业级 - 审批客户发布'),
            (gen_random_uuid(), 'sal:category:manage', '客户分类管理', 'sal', '企业级 - 管理客户分类'),
            (gen_random_uuid(), 'sal:credit:manage', '信用额度管理', 'sal', '企业级 - 配置客户信用额度'),
            (gen_random_uuid(), 'sal:pricing:manage', '价格体系管理', 'sal', '企业级 - 配置客户价格体系'),
            (gen_random_uuid(), 'sal:pricing:approve', '审批价格体系', 'sal', '企业级 - 审批价格体系发布'),
            (gen_random_uuid(), 'sal:quotation:create', '创建销售报价', 'sal', '企业级 - 创建销售报价单'),
            (gen_random_uuid(), 'sal:quotation:approve', '审批销售报价', 'sal', '企业级 - 审批销售报价单'),
            (gen_random_uuid(), 'sal:quotation:convert', '报价转单', 'sal', '企业级 - 报价单转销售订单'),
            (gen_random_uuid(), 'sal:quotation:cancel', '取消销售报价', 'sal', '企业级 - 取消销售报价单'),
            (gen_random_uuid(), 'sal:quotation:query', '查询销售报价', 'sal', '企业级 - 查询销售报价列表'),
            (gen_random_uuid(), 'sal:order:create', '创建销售订单', 'sal', '企业级 - 创建销售订单'),
            (gen_random_uuid(), 'sal:order:approve', '审批销售订单', 'sal', '企业级 - 审批销售订单'),
            (gen_random_uuid(), 'sal:order:confirm', '确认履约', 'sal', '企业级 - 确认履约触发库存预留'),
            (gen_random_uuid(), 'sal:order:change', '变更销售订单', 'sal', '企业级 - 变更已审批销售订单'),
            (gen_random_uuid(), 'sal:order:cancel', '取消销售订单', 'sal', '企业级 - 取消销售订单'),
            (gen_random_uuid(), 'sal:order:close', '关闭销售订单', 'sal', '企业级 - 关闭已完成的销售订单'),
            (gen_random_uuid(), 'sal:order:query', '查询销售订单', 'sal', '企业级 - 查询销售订单列表与详情'),
            (gen_random_uuid(), 'sal:shipment:create', '创建发货单', 'sal', '企业级 - 创建发货单触发WMS拣货'),
            (gen_random_uuid(), 'sal:shipment:confirm', '确认发货', 'sal', '企业级 - 确认发货触发WMS发货'),
            (gen_random_uuid(), 'sal:shipment:query', '查询发货', 'sal', '企业级 - 查询发货单列表'),
            (gen_random_uuid(), 'sal:return:create', '创建销售退货', 'sal', '企业级 - 发起销售退货申请'),
            (gen_random_uuid(), 'sal:return:approve', '审批销售退货', 'sal', '企业级 - 审批销售退货申请'),
            (gen_random_uuid(), 'sal:return:query', '查询销售退货', 'sal', '企业级 - 查询销售退货记录'),
            (gen_random_uuid(), 'sal:settlement:execute', '执行销售结算', 'sal', '企业级 - 执行销售对账与结算'),
            (gen_random_uuid(), 'sal:invoice:manage', '发票管理', 'sal', '企业级 - 管理销售发票与匹配'),
            (gen_random_uuid(), 'sal:payment:request', '收款申请', 'sal', '企业级 - 发起收款申请'),
            (gen_random_uuid(), 'sal:payment:confirm', '收款确认', 'sal', '企业级 - 确认收款完成'),
            (gen_random_uuid(), 'sal:reconcile:execute', '销售对账', 'sal', '企业级 - 执行销售WMS INV三边对账')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    # 移除权限
    op.execute("DELETE FROM iam_permission WHERE module = 'sal'")

    # 移除审计 Trigger
    op.execute("DROP TRIGGER IF EXISTS sal_audit_no_delete ON sal_sales_audit")
    op.execute("DROP TRIGGER IF EXISTS sal_audit_no_update ON sal_sales_audit")
    op.execute("DROP FUNCTION IF EXISTS trg_sal_audit_no_delete()")
    op.execute("DROP FUNCTION IF EXISTS trg_sal_audit_no_update()")

    # 恢复审计表写权限
    op.execute("GRANT UPDATE, DELETE ON sal_sales_audit TO public")

    # 移除 RLS 策略
    for tbl in _SAL_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_service ON {tbl}")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_tenant ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")