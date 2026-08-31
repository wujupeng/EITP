"""MDM 治理工作流与版本管理表 - 版本表 append-only。

Revision ID: 023
Revises: 022
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_governance_workflow ("
        "    request_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID,"
        "    governance_level       VARCHAR(10) NOT NULL,"
        "    entity_type            VARCHAR(30) NOT NULL,"
        "    entity_id              UUID,"
        "    target_version_id      UUID NOT NULL,"
        "    status                 VARCHAR(15) NOT NULL DEFAULT 'draft',"
        "    submitted_by           UUID,"
        "    submitted_at           TIMESTAMPTZ,"
        "    approved_by            UUID,"
        "    approved_at            TIMESTAMPTZ,"
        "    approval_opinion       VARCHAR(512),"
        "    published_by           UUID,"
        "    published_at           TIMESTAMPTZ,"
        "    rollback_by            UUID,"
        "    rollback_at            TIMESTAMPTZ,"
        "    rollback_reason        VARCHAR(512),"
        "    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    CONSTRAINT chk_mdm_gov_level CHECK (governance_level IN ('group', 'enterprise')),"
        "    CONSTRAINT chk_mdm_gov_status CHECK (status IN ('draft', 'submitted', 'approved', 'rejected', 'published', 'rolled_back')),"
        "    CONSTRAINT chk_mdm_gov_tenant CHECK ("
        "        (governance_level = 'group' AND tenant_id IS NULL) OR"
        "        (governance_level = 'enterprise' AND tenant_id IS NOT NULL)"
        "    )"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_gov_tenant ON mdm_governance_workflow (tenant_id)")
    op.execute("CREATE INDEX idx_mdm_gov_status ON mdm_governance_workflow (status)")
    op.execute("CREATE INDEX idx_mdm_gov_entity ON mdm_governance_workflow (entity_type, entity_id)")

    op.execute(
        "CREATE TABLE mdm_master_data_version ("
        "    version_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID,"
        "    entity_type            VARCHAR(30) NOT NULL,"
        "    entity_id              UUID NOT NULL,"
        "    version_number         INT NOT NULL,"
        "    snapshot_before        JSONB,"
        "    snapshot_after         JSONB NOT NULL,"
        "    change_type            VARCHAR(10) NOT NULL,"
        "    operated_by            UUID NOT NULL,"
        "    operated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    reason                 VARCHAR(512),"
        "    CONSTRAINT chk_mdm_version_change_type CHECK (change_type IN ('create', 'update', 'disable', 'enable', 'publish', 'rollback'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_version_entity ON mdm_master_data_version (entity_type, entity_id, version_number)")
    op.execute("CREATE INDEX idx_mdm_version_tenant ON mdm_master_data_version (tenant_id)")

    op.execute("REVOKE UPDATE, DELETE ON mdm_master_data_version FROM eitp")
    op.execute(
        "CREATE OR REPLACE FUNCTION fn_mdm_version_append_only() RETURNS TRIGGER AS $$ "
        "BEGIN "
        "    RAISE EXCEPTION 'EITP_MDM_VERSION_APPEND_ONLY: MasterDataVersion is append-only, UPDATE/DELETE forbidden'; "
        "END; "
        "$$ LANGUAGE plpgsql"
    )
    op.execute("CREATE TRIGGER trg_mdm_version_no_update BEFORE UPDATE ON mdm_master_data_version FOR EACH ROW EXECUTE FUNCTION fn_mdm_version_append_only()")
    op.execute("CREATE TRIGGER trg_mdm_version_no_delete BEFORE DELETE ON mdm_master_data_version FOR EACH ROW EXECUTE FUNCTION fn_mdm_version_append_only()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_version_no_delete ON mdm_master_data_version")
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_version_no_update ON mdm_master_data_version")
    op.execute("DROP FUNCTION IF EXISTS fn_mdm_version_append_only()")
    op.execute("DROP TABLE IF EXISTS mdm_master_data_version CASCADE")
    op.execute("DROP TABLE IF EXISTS mdm_governance_workflow CASCADE")