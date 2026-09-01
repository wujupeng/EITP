"""SAL 客户主数据表 - 客户/地址/联系人/分类/信用额度/价格体系。

Revision ID: 039
Revises: 038
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sal_customer (
            customer_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            customer_code        VARCHAR(64) NOT NULL,
            customer_name        VARCHAR(256) NOT NULL,
            customer_type        VARCHAR(32) NOT NULL DEFAULT 'corporate',
            tax_id               VARCHAR(64) NOT NULL DEFAULT '',
            contact_info         JSONB NOT NULL DEFAULT '{}'::jsonb,
            bank_account         JSONB NOT NULL DEFAULT '{}'::jsonb,
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            published_version    INTEGER NOT NULL DEFAULT 0,
            governance_state     VARCHAR(32) NOT NULL DEFAULT 'draft',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_customer_code UNIQUE (tenant_id, customer_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_customer_tenant_status ON sal_customer (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_customer_address (
            address_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            address_type         VARCHAR(32) NOT NULL DEFAULT 'default',
            is_default           BOOLEAN NOT NULL DEFAULT FALSE,
            is_shipping          BOOLEAN NOT NULL DEFAULT FALSE,
            is_billing           BOOLEAN NOT NULL DEFAULT FALSE,
            province             VARCHAR(64) NOT NULL DEFAULT '',
            city                 VARCHAR(64) NOT NULL DEFAULT '',
            district             VARCHAR(64) NOT NULL DEFAULT '',
            detail               VARCHAR(256) NOT NULL DEFAULT '',
            receiver_name        VARCHAR(128) NOT NULL DEFAULT '',
            receiver_phone       VARCHAR(32) NOT NULL DEFAULT '',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_cust_addr_customer ON sal_customer_address (tenant_id, customer_id)")

    op.execute("""
        CREATE TABLE sal_customer_contact (
            contact_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            contact_name         VARCHAR(128) NOT NULL DEFAULT '',
            position             VARCHAR(64) NOT NULL DEFAULT '',
            phone                VARCHAR(32) NOT NULL DEFAULT '',
            email                VARCHAR(128) NOT NULL DEFAULT '',
            is_primary           BOOLEAN NOT NULL DEFAULT FALSE,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_cust_contact_customer ON sal_customer_contact (tenant_id, customer_id)")

    op.execute("""
        CREATE TABLE sal_customer_category (
            category_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            category_code        VARCHAR(64) NOT NULL,
            category_name        VARCHAR(256) NOT NULL,
            description          VARCHAR(512) NOT NULL DEFAULT '',
            status               VARCHAR(32) NOT NULL DEFAULT 'active',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_category_code UNIQUE (tenant_id, category_code)
        )
    """)
    op.execute("CREATE INDEX idx_sal_category_tenant_status ON sal_customer_category (tenant_id, status)")

    op.execute("""
        CREATE TABLE sal_credit_limit (
            credit_limit_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            customer_id          UUID NOT NULL REFERENCES sal_customer(customer_id),
            total_limit          NUMERIC(18,6) NOT NULL DEFAULT 0,
            used_amount          NUMERIC(18,6) NOT NULL DEFAULT 0,
            credit_period_days   INTEGER NOT NULL DEFAULT 30,
            over_credit_strategy VARCHAR(32) NOT NULL DEFAULT 'block',
            version              INTEGER NOT NULL DEFAULT 1,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_sal_credit_limit_customer UNIQUE (tenant_id, customer_id)
        )
    """)
    op.execute("CREATE INDEX idx_sal_credit_limit_customer ON sal_credit_limit (tenant_id, customer_id)")

    op.execute("""
        CREATE TABLE sal_customer_pricing (
            pricing_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id            UUID NOT NULL,
            customer_id          UUID,
            category_id          UUID,
            enterprise_sku_id    UUID NOT NULL,
            price_type           VARCHAR(32) NOT NULL DEFAULT 'standard',
            agreement_price      NUMERIC(18,6),
            discount_rate        NUMERIC(6,4),
            promotion_id         UUID,
            priority             INTEGER NOT NULL DEFAULT 4,
            valid_from           TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_until          TIMESTAMPTZ,
            status               VARCHAR(32) NOT NULL DEFAULT 'draft',
            governance_state     VARCHAR(32) NOT NULL DEFAULT 'draft',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_sal_pricing_customer ON sal_customer_pricing (tenant_id, customer_id)")
    op.execute("CREATE INDEX idx_sal_pricing_category ON sal_customer_pricing (tenant_id, category_id)")
    op.execute("CREATE INDEX idx_sal_pricing_sku ON sal_customer_pricing (tenant_id, enterprise_sku_id)")


def downgrade() -> None:
    for tbl in [
        "sal_customer_pricing", "sal_credit_limit", "sal_customer_category",
        "sal_customer_contact", "sal_customer_address", "sal_customer",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")