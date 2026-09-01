"""SEC 认证元数据表（5 张表）。

Revision ID: 045
Revises: 044
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sec_certification_batch",
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("matrix_version", sa.String(32), nullable=False),
        sa.Column("trigger_source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("passed_count", sa.Integer, server_default="0"),
        sa.Column("failed_count", sa.Integer, server_default="0"),
        sa.Column("unexecutable_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "sec_certification_item",
        sa.Column("item_id", sa.String(128), primary_key=True),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_certification_batch.batch_id"), nullable=False),
        sa.Column("layer", sa.String(32), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("aggregate_root", sa.String(64), nullable=False),
        sa.Column("attack_vector", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("expected_behavior", sa.String(256)),
        sa.Column("actual_behavior", sa.String(256)),
        sa.Column("conclusion", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("evidence", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Float, server_default="0"),
        sa.Column("failure_reason", sa.String(512)),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "sec_certification_report",
        sa.Column("report_id", sa.String(64), primary_key=True),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_certification_batch.batch_id"), nullable=False),
        sa.Column("matrix_version", sa.String(32), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("executor", sa.String(64)),
        sa.Column("total_items", sa.Integer, server_default="0"),
        sa.Column("passed_count", sa.Integer, server_default="0"),
        sa.Column("failed_count", sa.Integer, server_default="0"),
        sa.Column("unexecutable_count", sa.Integer, server_default="0"),
        sa.Column("pass_rate", sa.Float, server_default="0"),
        sa.Column("failed_items", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("evidence_index", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("report_json", sa.dialects.postgresql.JSONB),
        sa.Column("report_html", sa.Text),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "sec_certification_certificate",
        sa.Column("certificate_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cert_number", sa.String(64), nullable=False, unique=True),
        sa.Column("matrix_version", sa.String(32), nullable=False),
        sa.Column("cert_scope", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("issuer", sa.String(64)),
        sa.Column("signer", sa.String(64)),
        sa.Column("evidence_hash", sa.String(64)),
        sa.Column("signature", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_table(
        "sec_certification_config",
        sa.Column("config_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("matrix_layers", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("strict_mode", sa.Boolean, server_default=sa.text("true")),
        sa.Column("alert_channels", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'")),
        sa.Column("report_retention_days", sa.Integer, server_default="365"),
        sa.Column("item_skip_reasons", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'")),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sec_certification_config")
    op.drop_table("sec_certification_certificate")
    op.drop_table("sec_certification_report")
    op.drop_table("sec_certification_item")
    op.drop_table("sec_certification_batch")