"""SQLAlchemy 异步基类 - 所有 ORM 模型的公共基类。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""


class TimestampMixin:
    """时间戳混入 - created_at / updated_at 自动维护。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantScopedMixin:
    """租户作用混入 - 标记需要 tenant_id 隔离的实体。

    被 TenantFilterEvent 识别，查询时自动追加 WHERE tenant_id = :ctx_tenant_id。
    """

    __tenant_scoped__ = True