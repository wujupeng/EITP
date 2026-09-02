"""PLT Outbox + Saga 表。

Revision ID: 051
Revises: 050
Create Date: 2026-09-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plt_outbox_event",
        sa.Column("event_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_root_type", sa.String(64), nullable=False),
        sa.Column("aggregate_root_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("event_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivery_status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("delivery_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True)),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="10"),
    )

    op.create_table(
        "plt_saga_instance",
        sa.Column("saga_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("saga_type", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="RUNNING"),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("steps", sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("compensations", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("plt_saga_instance")
    op.drop_table("plt_outbox_event")