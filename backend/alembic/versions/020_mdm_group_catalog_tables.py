"""MDM 集团商品目录表 - 集团级，无 tenant_id。

Revision ID: 020
Revises: 010
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "020"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_group_product ("
        "    group_product_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    group_product_code    VARCHAR(64) NOT NULL,"
        "    group_product_name    VARCHAR(256) NOT NULL,"
        "    group_category_id     UUID,"
        "    group_brand_id        UUID,"
        "    base_unit_id          UUID NOT NULL,"
        "    spec_template_id      UUID,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    published_version     INT NOT NULL DEFAULT 1,"
        "    description           VARCHAR(1024),"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_product_code UNIQUE (group_product_code),"
        "    CONSTRAINT chk_mdm_group_product_status CHECK (status IN ('active', 'disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_group_product_category ON mdm_group_product (group_category_id)")
    op.execute("CREATE INDEX idx_mdm_group_product_brand ON mdm_group_product (group_brand_id)")
    op.execute("CREATE INDEX idx_mdm_group_product_status ON mdm_group_product (status)")

    op.execute(
        "CREATE TABLE mdm_group_sku ("
        "    group_sku_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    group_product_id      UUID NOT NULL,"
        "    group_sku_code        VARCHAR(64) NOT NULL,"
        "    group_sku_name        VARCHAR(256) NOT NULL,"
        "    specification_instance JSONB,"
        "    barcode_list          JSONB,"
        "    unit_id               UUID NOT NULL,"
        "    weight                NUMERIC(18,6),"
        "    volume                NUMERIC(18,6),"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_sku_code UNIQUE (group_sku_code),"
        "    CONSTRAINT chk_mdm_group_sku_status CHECK (status IN ('active', 'disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_group_sku_product ON mdm_group_sku (group_product_id)")
    op.execute("CREATE INDEX idx_mdm_group_sku_barcode ON mdm_group_sku USING gin (barcode_list)")

    op.execute(
        "CREATE TABLE mdm_group_category ("
        "    group_category_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    group_category_code   VARCHAR(64) NOT NULL,"
        "    group_category_name   VARCHAR(128) NOT NULL,"
        "    parent_category_id    UUID,"
        "    level                 INT NOT NULL,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    published_version     INT NOT NULL DEFAULT 1,"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_category_code UNIQUE (group_category_code),"
        "    CONSTRAINT chk_mdm_group_category_status CHECK (status IN ('active', 'disabled'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_group_category_parent ON mdm_group_category (parent_category_id)")

    op.execute(
        "CREATE TABLE mdm_group_brand ("
        "    group_brand_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    group_brand_code      VARCHAR(64) NOT NULL,"
        "    group_brand_name      VARCHAR(128) NOT NULL,"
        "    status                VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_brand_code UNIQUE (group_brand_code)"
        ")"
    )

    op.execute(
        "CREATE TABLE mdm_group_unit ("
        "    group_unit_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    group_unit_code       VARCHAR(32) NOT NULL,"
        "    group_unit_name       VARCHAR(64) NOT NULL,"
        "    is_base_unit          BOOLEAN NOT NULL,"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_unit_code UNIQUE (group_unit_code)"
        ")"
    )
    op.execute(
        "CREATE TABLE mdm_group_unit_conversion ("
        "    conversion_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    from_unit_id          UUID NOT NULL,"
        "    to_unit_id            UUID NOT NULL,"
        "    ratio                 NUMERIC(18,6) NOT NULL CHECK (ratio > 0),"
        "    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT uk_mdm_group_unit_conversion UNIQUE (from_unit_id, to_unit_id)"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mdm_group_unit_conversion CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_group_unit CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_group_brand CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_group_category CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_group_sku CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_group_product CASCADE")