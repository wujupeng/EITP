"""REL 复合索引 + PostgreSQL 角色权限扩展。

Revision ID: 069
Revises: 068
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None

_REL_TABLES = [
    "rel_release",
    "rel_asset_snapshot",
    "rel_core_freeze_declaration",
    "rel_seal_gate_record",
    "rel_rollback_plan",
]


def upgrade() -> None:
    op.create_index("idx_rel_asset_release_type", "rel_asset_snapshot", ["release_id", "asset_type"])
    op.create_index("idx_rel_gate_release_type", "rel_seal_gate_record", ["release_id", "gate_type"])

    op.execute("DO $$ BEGIN CREATE ROLE eitp_rel_service_role NOLOGIN; EXCEPTION WHEN DUPLICATE_OBJECT THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE ROLE eitp_rel_admin_role NOLOGIN; EXCEPTION WHEN DUPLICATE_OBJECT THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT ON {tbl} TO eitp_rel_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_rel_admin_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT ON {tbl} TO eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY; EXCEPTION WHEN undefined_table THEN NULL; END $$")


def downgrade() -> None:
    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE SELECT ON {tbl} FROM eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE ALL ON {tbl} FROM eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE ALL ON {tbl} FROM eitp_rel_admin_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _REL_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE SELECT, INSERT ON {tbl} FROM eitp_rel_service_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    op.drop_index("idx_rel_gate_release_type", table_name="rel_seal_gate_record")
    op.drop_index("idx_rel_asset_release_type", table_name="rel_asset_snapshot")