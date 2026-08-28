"""层级模型 ORM - HierarchyNode 表 + HierarchyClosure 闭包表。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TenantScopedMixin, TimestampMixin


class HierarchyNodeORM(Base, TimestampMixin, TenantScopedMixin):
    """层级节点 ORM 模型。"""

    __tablename__ = "hierarchy_node"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hierarchy_node.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class HierarchyClosureORM(Base):
    """层级闭包表 - 存储祖先-后代关系与深度。

    每个节点至少有一条自引用记录（ancestor=descendant, depth=0）。
    查询某节点的所有祖先：WHERE descendant_id = :node_id
    查询某节点的所有后代：WHERE ancestor_id = :node_id
    """

    __tablename__ = "hierarchy_closure"

    ancestor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hierarchy_node.id", ondelete="CASCADE"),
        primary_key=True,
    )
    descendant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("hierarchy_node.id", ondelete="CASCADE"),
        primary_key=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

    __table_args__ = (
        Index("idx_closure_descendant", "descendant_id"),
        Index("idx_closure_ancestor", "ancestor_id"),
        Index("idx_closure_tenant", "tenant_id"),
    )