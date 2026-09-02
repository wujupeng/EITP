"""PROD PostgreSQL 角色权限扩展。

Revision ID: 064
Revises: 063
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None

_PROD_TABLES = [
    "prod_verification_run",
    "prod_verification_evidence",
    "prod_readiness_dossier",
]


def upgrade() -> None:
    for tbl in _PROD_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT, INSERT ON {tbl} TO eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    op.execute("DO $$ BEGIN REVOKE UPDATE, DELETE ON prod_verification_run FROM eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE UPDATE, DELETE ON prod_verification_evidence FROM eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
    op.execute("DO $$ BEGIN REVOKE DELETE ON prod_readiness_dossier FROM eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _PROD_TABLES:
        op.execute(f"DO $$ BEGIN GRANT ALL ON {tbl} TO eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")

    for tbl in _PROD_TABLES:
        op.execute(f"DO $$ BEGIN GRANT SELECT ON {tbl} TO eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")


def downgrade() -> None:
    for tbl in _PROD_TABLES:
        op.execute(f"DO $$ BEGIN REVOKE ALL ON {tbl} FROM eitp_platform_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
        op.execute(f"DO $$ BEGIN REVOKE SELECT, INSERT ON {tbl} FROM eitp_app_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")
        op.execute(f"DO $$ BEGIN REVOKE SELECT ON {tbl} FROM eitp_readonly_role; EXCEPTION WHEN undefined_table THEN NULL; END $$")