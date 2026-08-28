"""hierarchy tables

Revision ID: 002
Revises: 001
Create Date: 2026-08-27 00:01:00

EITP-MT-001-T02-03: 创建层级节点表与闭包表。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hierarchy_node",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["parent_id"], ["hierarchy_node.id"], ondelete="RESTRICT"),
    )
    op.create_index("idx_hierarchy_node_tenant", "hierarchy_node", ["tenant_id"])

    op.create_table(
        "hierarchy_closure",
        sa.Column("ancestor_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hierarchy_node.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("descendant_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("hierarchy_node.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("depth", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_closure_descendant", "hierarchy_closure", ["descendant_id"])
    op.create_index("idx_closure_ancestor", "hierarchy_closure", ["ancestor_id"])
    op.create_index("idx_closure_tenant", "hierarchy_closure", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("idx_closure_tenant", table_name="hierarchy_closure")
    op.drop_index("idx_closure_ancestor", table_name="hierarchy_closure")
    op.drop_index("idx_closure_descendant", table_name="hierarchy_closure")
    op.drop_table("hierarchy_closure")
    op.drop_index("idx_hierarchy_node_tenant", table_name="hierarchy_node")
    op.drop_table("hierarchy_node")