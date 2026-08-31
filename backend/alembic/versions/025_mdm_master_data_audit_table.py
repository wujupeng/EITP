"""MDM 主数据审计表 - append-only，不可篡改。

Revision ID: 025
Revises: 024
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_master_data_audit ("
        "    audit_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID,"
        "    action                 VARCHAR(40) NOT NULL,"
        "    entity_type            VARCHAR(30) NOT NULL,"
        "    entity_id              UUID NOT NULL,"
        "    version_number         INT,"
        "    old_value              JSONB,"
        "    new_value              JSONB,"
        "    operated_by            UUID NOT NULL,"
        "    operated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    reason                 VARCHAR(512),"
        "    ip_address             VARCHAR(45)"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_md_audit_tenant ON mdm_master_data_audit (tenant_id, operated_at DESC)")
    op.execute("CREATE INDEX idx_mdm_md_audit_entity ON mdm_master_data_audit (entity_type, entity_id)")

    op.execute("REVOKE UPDATE, DELETE ON mdm_master_data_audit FROM eitp")
    op.execute("CREATE TRIGGER trg_mdm_md_audit_no_update BEFORE UPDATE ON mdm_master_data_audit FOR EACH ROW EXECUTE FUNCTION fn_mdm_version_append_only()")
    op.execute("CREATE TRIGGER trg_mdm_md_audit_no_delete BEFORE DELETE ON mdm_master_data_audit FOR EACH ROW EXECUTE FUNCTION fn_mdm_version_append_only()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_md_audit_no_delete ON mdm_master_data_audit")
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_md_audit_no_update ON mdm_master_data_audit")
    op.execute("DROP TABLE IF EXISTS mdm_master_data_audit CASCADE")