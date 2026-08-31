"""MDM 企业商品与引用关系表 - 企业级，含 tenant_id。

Revision ID: 021
Revises: 020
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_enterprise_product ("
        "    enterprise_product_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id               UUID NOT NULL,"
        "    group_product_id        UUID NOT NULL,"
        "    enterprise_product_code VARCHAR(64) NOT NULL,"
        "    enterprise_product_name VARCHAR(256),"
        "    enterprise_category_id  UUID,"
        "    reference_status        VARCHAR(20) NOT NULL DEFAULT 'active',"
        "    published_version       INT NOT NULL DEFAULT 1,"
        "    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_ep_tenant_code UNIQUE (tenant_id, enterprise_product_code),"
        "    CONSTRAINT chk_mdm_ep_ref_status CHECK (reference_status IN ('active', 'reference_released', 'source_disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_ep_tenant ON mdm_enterprise_product (tenant_id)")
    op.execute("CREATE INDEX idx_mdm_ep_group_product ON mdm_enterprise_product (tenant_id, group_product_id)")

    op.execute(
        "CREATE TABLE mdm_enterprise_sku ("
        "    enterprise_sku_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id               UUID NOT NULL,"
        "    enterprise_product_id   UUID NOT NULL,"
        "    group_sku_id            UUID NOT NULL,"
        "    enterprise_sku_code     VARCHAR(64),"
        "    enterprise_sku_name     VARCHAR(256),"
        "    enterprise_barcode_list JSONB,"
        "    status                  VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_esku_tenant_code UNIQUE (tenant_id, enterprise_sku_code)"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_esku_tenant ON mdm_enterprise_sku (tenant_id)")
    op.execute("CREATE INDEX idx_mdm_esku_product ON mdm_enterprise_sku (tenant_id, enterprise_product_id)")
    op.execute("CREATE INDEX idx_mdm_esku_barcode ON mdm_enterprise_sku USING gin (enterprise_barcode_list)")

    op.execute(
        "CREATE TABLE mdm_product_reference ("
        "    reference_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id               UUID NOT NULL,"
        "    group_product_id        UUID NOT NULL,"
        "    enterprise_product_id   UUID NOT NULL,"
        "    referenced_by           UUID NOT NULL,"
        "    referenced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    reference_status        VARCHAR(20) NOT NULL DEFAULT 'active',"
        "    released_by             UUID,"
        "    released_at             TIMESTAMPTZ,"
        "    CONSTRAINT uk_mdm_ref_tenant_group UNIQUE (tenant_id, group_product_id),"
        "    CONSTRAINT chk_mdm_ref_status CHECK (reference_status IN ('active', 'released', 'source_disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_ref_tenant ON mdm_product_reference (tenant_id)")
    op.execute("CREATE INDEX idx_mdm_ref_group_product ON mdm_product_reference (group_product_id)")

    op.execute(
        "CREATE TABLE mdm_product_customization ("
        "    customization_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id               UUID NOT NULL,"
        "    enterprise_product_id   UUID NOT NULL,"
        "    enterprise_sku_id       UUID,"
        "    sales_price             NUMERIC(18,6),"
        "    purchase_price          NUMERIC(18,6),"
        "    inventory_strategy      VARCHAR(10),"
        "    safety_stock            NUMERIC(18,6),"
        "    cost_model              VARCHAR(20),"
        "    custom_attributes       JSONB,"
        "    version                 INT NOT NULL DEFAULT 1,"
        "    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_mdm_cust_inv_strategy CHECK (inventory_strategy IN ('strict', 'allow', 'warning', 'approval')),"
        "    CONSTRAINT chk_mdm_cust_cost_model CHECK (cost_model IN ('moving_average', 'weighted_average', 'fifo', 'standard_cost', 'actual_cost'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_cust_tenant_product ON mdm_product_customization (tenant_id, enterprise_product_id)")
    op.execute("CREATE INDEX idx_mdm_cust_tenant_sku ON mdm_product_customization (tenant_id, enterprise_sku_id)")

    op.execute(
        "CREATE TABLE mdm_enterprise_category ("
        "    enterprise_category_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id                 UUID NOT NULL,"
        "    enterprise_category_code  VARCHAR(64) NOT NULL,"
        "    enterprise_category_name  VARCHAR(128) NOT NULL,"
        "    parent_category_id        UUID,"
        "    parent_category_level     VARCHAR(10),"
        "    level                     INT NOT NULL,"
        "    status                    VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_ec_tenant_code UNIQUE (tenant_id, enterprise_category_code),"
        "    CONSTRAINT chk_mdm_ec_parent_level CHECK (parent_category_level IN ('group', 'enterprise')),"
        "    CONSTRAINT chk_mdm_ec_status CHECK (status IN ('active', 'disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_ec_tenant ON mdm_enterprise_category (tenant_id)")
    op.execute("CREATE INDEX idx_mdm_ec_parent ON mdm_enterprise_category (tenant_id, parent_category_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mdm_enterprise_category CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_product_customization CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_product_reference CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_enterprise_sku CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_enterprise_product CASCADE")