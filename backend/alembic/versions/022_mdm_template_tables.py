"""MDM 规格模板与属性模板表。

Revision ID: 022
Revises: 021
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_spec_template ("
        "    template_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID,"
        "    template_level         VARCHAR(10) NOT NULL,"
        "    template_code          VARCHAR(64) NOT NULL,"
        "    template_name          VARCHAR(128) NOT NULL,"
        "    attribute_definitions  JSONB NOT NULL,"
        "    status                 VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_mdm_spec_template_level CHECK (template_level IN ('group', 'enterprise')),"
        "    CONSTRAINT chk_mdm_spec_template_status CHECK (status IN ('active', 'disabled')),"
        "    CONSTRAINT chk_mdm_spec_template_tenant CHECK ("
        "        (template_level = 'group' AND tenant_id IS NULL) OR"
        "        (template_level = 'enterprise' AND tenant_id IS NOT NULL)"
        "    )"
        ")"
    )
    op.execute("CREATE UNIQUE INDEX uk_mdm_spec_template_group_code ON mdm_spec_template (template_code) WHERE template_level = 'group'")
    op.execute("CREATE UNIQUE INDEX uk_mdm_spec_template_tenant_code ON mdm_spec_template (tenant_id, template_code) WHERE template_level = 'enterprise'")
    op.execute("CREATE INDEX idx_mdm_spec_template_tenant ON mdm_spec_template (tenant_id)")

    op.execute(
        "CREATE TABLE mdm_attribute_template ("
        "    template_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID,"
        "    template_level         VARCHAR(10) NOT NULL,"
        "    template_code          VARCHAR(64) NOT NULL,"
        "    template_name          VARCHAR(128) NOT NULL,"
        "    attribute_name         VARCHAR(64) NOT NULL,"
        "    attribute_type         VARCHAR(10) NOT NULL,"
        "    enum_values            JSONB,"
        "    is_required            BOOLEAN NOT NULL DEFAULT false,"
        "    status                 VARCHAR(10) NOT NULL DEFAULT 'active',"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_mdm_attr_template_level CHECK (template_level IN ('group', 'enterprise')),"
        "    CONSTRAINT chk_mdm_attr_template_type CHECK (attribute_type IN ('text', 'number', 'enum', 'date', 'boolean')),"
        "    CONSTRAINT chk_mdm_attr_template_status CHECK (status IN ('active', 'disabled')),"
        "    CONSTRAINT chk_mdm_attr_template_tenant CHECK ("
        "        (template_level = 'group' AND tenant_id IS NULL) OR"
        "        (template_level = 'enterprise' AND tenant_id IS NOT NULL)"
        "    )"
        ")"
    )
    op.execute("CREATE UNIQUE INDEX uk_mdm_attr_template_group_code ON mdm_attribute_template (template_code, attribute_name) WHERE template_level = 'group'")
    op.execute("CREATE UNIQUE INDEX uk_mdm_attr_template_tenant_code ON mdm_attribute_template (tenant_id, template_code, attribute_name) WHERE template_level = 'enterprise'")
    op.execute("CREATE INDEX idx_mdm_attr_template_tenant ON mdm_attribute_template (tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mdm_attribute_template CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_spec_template CASCADE")