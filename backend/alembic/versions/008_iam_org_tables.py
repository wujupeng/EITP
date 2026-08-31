"""IAM org tables

Revision ID: 008
Revises: 007
Create Date: 2026-08-29 00:00:03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iam_department",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_dept_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_department.id"), nullable=True),
        sa.Column("org_node_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "iam_position",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dept_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_department.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "iam_user_position",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_position.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "iam_user_org_scope",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("iam_user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("org_node_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("iam_user_org_scope")
    op.drop_table("iam_user_position")
    op.drop_table("iam_position")
    op.drop_table("iam_department")