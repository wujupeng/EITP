"""MDM 负库存策略审计表 - append-only，不可篡改。

Revision ID: 024
Revises: 023
Create Date: 2026-08-30
"""

from __future__ import annotations

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE mdm_negative_inventory_policy_audit ("
        "    audit_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
        "    tenant_id              UUID NOT NULL,"
        "    policy_before          VARCHAR(10) NOT NULL,"
        "    policy_after           VARCHAR(10) NOT NULL,"
        "    operated_by            UUID NOT NULL,"
        "    operated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "    reason                 VARCHAR(512) NOT NULL,"
        "    CONSTRAINT chk_mdm_neg_audit_before CHECK (policy_before IN ('strict', 'allow', 'warning', 'approval')),"
        "    CONSTRAINT chk_mdm_neg_audit_after CHECK (policy_after IN ('strict', 'allow', 'warning', 'approval'))"
        ")"
    )
    op.execute("CREATE INDEX idx_mdm_neg_audit_tenant ON mdm_negative_inventory_policy_audit (tenant_id, operated_at DESC)")

    op.execute("REVOKE UPDATE, DELETE ON mdm_negative_inventory_policy_audit FROM eitp")
    op.execute(
        "CREATE OR REPLACE FUNCTION fn_mdm_neg_audit_append_only() RETURNS TRIGGER AS $$ "
        "BEGIN "
        "    RAISE EXCEPTION 'EITP_MDM_NEG_POLICY_AUDIT_APPEND_ONLY: NegativeInventoryPolicyAudit is append-only, UPDATE/DELETE forbidden'; "
        "END; "
        "$$ LANGUAGE plpgsql"
    )
    op.execute("CREATE TRIGGER trg_mdm_neg_audit_no_update BEFORE UPDATE ON mdm_negative_inventory_policy_audit FOR EACH ROW EXECUTE FUNCTION fn_mdm_neg_audit_append_only()")
    op.execute("CREATE TRIGGER trg_mdm_neg_audit_no_delete BEFORE DELETE ON mdm_negative_inventory_policy_audit FOR EACH ROW EXECUTE FUNCTION fn_mdm_neg_audit_append_only()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_neg_audit_no_delete ON mdm_negative_inventory_policy_audit")
    op.execute("DROP TRIGGER IF EXISTS trg_mdm_neg_audit_no_update ON mdm_negative_inventory_policy_audit")
    op.execute("DROP FUNCTION IF EXISTS fn_mdm_neg_audit_append_only()")
    op.execute("DROP TABLE IF EXISTS mdm_negative_inventory_policy_audit CASCADE")