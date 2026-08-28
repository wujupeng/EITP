"""group summary snapshot tables

Revision ID: 003
Revises: 002
Create Date: 2026-08-28 00:01:00

EITP-MT-001-T07-03: 创建集团汇总快照表与集团-子公司关联表。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_summary_snapshot",
        sa.Column("snapshot_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enterprise_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("snapshot_value", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_snapshot_enterprise", "group_summary_snapshot", ["enterprise_id"])
    op.create_index("idx_snapshot_organization", "group_summary_snapshot", ["organization_id"])
    op.create_index(
        "idx_snapshot_unique",
        "group_summary_snapshot",
        ["enterprise_id", "organization_id", "dimension"],
        unique=True,
    )

    op.create_table(
        "group_organization",
        sa.Column("enterprise_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("is_active", sa.String(1), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_group_org_enterprise", "group_organization", ["enterprise_id"])


def downgrade() -> None:
    op.drop_index("idx_group_org_enterprise", table_name="group_organization")
    op.drop_table("group_organization")
    op.drop_index("idx_snapshot_unique", table_name="group_summary_snapshot")
    op.drop_index("idx_snapshot_organization", table_name="group_summary_snapshot")
    op.drop_index("idx_snapshot_enterprise", table_name="group_summary_snapshot")
    op.drop_table("group_summary_snapshot")