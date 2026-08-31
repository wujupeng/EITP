"""MDM RLS 策略统一下发 + 23 个主数据操作权限注册。

Revision ID: 027
Revises: 026
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


_RLS_TABLES = [
    "mdm_enterprise_product",
    "mdm_enterprise_sku",
    "mdm_product_reference",
    "mdm_product_customization",
    "mdm_enterprise_category",
    "mdm_negative_inventory_policy_audit",
]

_RLS_TABLES_NULL_TENANT = [
    "mdm_governance_workflow",
    "mdm_master_data_version",
    "mdm_master_data_audit",
]

_MDM_PERMISSIONS = [
    ("mdm:group_product:manage", "管理集团商品", "mdm"),
    ("mdm:group_product:approve", "审批集团商品", "mdm"),
    ("mdm:group_sku:manage", "管理集团SKU", "mdm"),
    ("mdm:group_category:manage", "管理集团分类", "mdm"),
    ("mdm:group_brand:manage", "管理集团品牌", "mdm"),
    ("mdm:group_unit:manage", "管理集团单位", "mdm"),
    ("mdm:spec_template:manage", "管理规格模板", "mdm"),
    ("mdm:attribute_template:manage", "管理属性模板", "mdm"),
    ("mdm:enterprise_product:manage", "管理企业商品", "mdm"),
    ("mdm:enterprise_product:approve", "审批企业商品", "mdm"),
    ("mdm:enterprise_customization:manage", "管理企业定制", "mdm"),
    ("mdm:product_reference:create", "创建商品引用", "mdm"),
    ("mdm:product_reference:release", "释放商品引用", "mdm"),
    ("mdm:governance:submit", "提交治理申请", "mdm"),
    ("mdm:governance:approve", "审批治理申请", "mdm"),
    ("mdm:governance:publish", "发布治理结果", "mdm"),
    ("mdm:governance:rollback", "回滚治理版本", "mdm"),
    ("mdm:governance:query", "查询治理工作流", "mdm"),
    ("mdm:version:compare", "版本对比", "mdm"),
    ("mdm:version:query", "版本查询", "mdm"),
    ("mdm:negative_policy:config", "配置负库存策略", "mdm"),
    ("mdm:negative_policy:audit:query", "查询负库存策略审计", "mdm"),
    ("mdm:master_data:query", "查询主数据", "mdm"),
]


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY rls_{table}_tenant ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)"
        )

    for table in _RLS_TABLES_NULL_TENANT:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY rls_{table}_tenant ON {table} "
            f"USING (tenant_id IS NULL OR tenant_id = current_setting('app.current_tenant_id', true)::UUID)"
        )

    for code, name, module in _MDM_PERMISSIONS:
        op.execute(
            f"INSERT INTO iam_permission (id, code, name, module, description) "
            f"VALUES (gen_random_uuid(), '{code}', '{name}', '{module}', '{name}') "
            f"ON CONFLICT (code) DO NOTHING"
        )


def downgrade() -> None:
    for table in _RLS_TABLES + _RLS_TABLES_NULL_TENANT:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for code, _, _ in _MDM_PERMISSIONS:
        op.execute(f"DELETE FROM iam_permission WHERE code = '{code}'")
