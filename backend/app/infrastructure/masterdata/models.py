"""主数据 ORM 模型 - MasterDataBase + CompanyOverride + WarehouseOverride。"""

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


class MasterDataBaseORM(Base, TimestampMixin):
    """主数据基准 ORM - 集团层统一主数据。"""

    __tablename__ = "master_data_base"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    enterprise_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    sku_code: Mapped[str] = mapped_column(String(255), nullable=False)
    base_attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("idx_master_base_unique", "enterprise_id", "sku_code", unique=True),
    )


class CompanyOverrideORM(Base, TimestampMixin):
    """公司级属性覆盖 ORM。"""

    __tablename__ = "master_data_company_override"

    override_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    master_data_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("master_data_base.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    company_attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_company_override_unique", "master_data_id", "organization_id", unique=True),
    )


class WarehouseOverrideORM(Base, TimestampMixin):
    """仓库级属性覆盖 ORM。"""

    __tablename__ = "master_data_warehouse_override"

    override_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    master_data_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("master_data_base.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    warehouse_attrs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_warehouse_override_unique", "master_data_id", "warehouse_id", unique=True),
    )