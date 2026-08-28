"""集团报表 ORM 模型 - SummarySnapshot 表。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin


class SummarySnapshotORM(Base, TimestampMixin):
    """汇总快照 ORM - 跨公司汇总的最终一致缓存。

    (enterprise_id, organization_id, dimension) 唯一索引。
    """

    __tablename__ = "group_summary_snapshot"

    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    enterprise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index(
            "idx_snapshot_unique",
            "enterprise_id",
            "organization_id",
            "dimension",
            unique=True,
        ),
    )


class GroupOrganizationORM(Base, TimestampMixin):
    """集团-子公司关联 ORM - 记录 Enterprise 下辖的 Organization。"""

    __tablename__ = "group_organization"

    enterprise_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True
    )
    is_active: Mapped[bool] = mapped_column(
        String(1), nullable=False, default="1"
    )

    __table_args__ = (
        Index("idx_group_org_enterprise", "enterprise_id"),
    )