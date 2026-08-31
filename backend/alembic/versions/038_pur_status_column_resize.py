"""PUR status 列扩容 VARCHAR(16) -> VARCHAR(32)。

Revision ID: 038
Revises: 037
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


_PUR_STATUS_TABLES = [
    "pur_supplier",
    "pur_quotation",
    "pur_supplier_evaluation",
    "pur_purchase_request",
    "pur_purchase_order",
    "pur_asn",
    "pur_purchase_receipt",
    "pur_purchase_return",
    "pur_purchase_settlement",
    "pur_invoice",
    "pur_payment_request",
    "pur_reconcile_diff",
]


def upgrade() -> None:
    for tbl in _PUR_STATUS_TABLES:
        op.execute(f"ALTER TABLE {tbl} ALTER COLUMN status TYPE VARCHAR(32)")


def downgrade() -> None:
    for tbl in _PUR_STATUS_TABLES:
        op.execute(f"ALTER TABLE {tbl} ALTER COLUMN status TYPE VARCHAR(16)")