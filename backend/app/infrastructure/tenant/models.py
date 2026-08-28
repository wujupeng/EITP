"""租户 ORM 模型。"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin


class TenantORM(Base, TimestampMixin):
    """租户 ORM 模型 - 平台级表，非租户隔离。"""

    __tablename__ = "tenant"
    __tenant_scoped__ = False

    id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    enterprise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="provisioning")
    data_placement: Mapped[str] = mapped_column(String(50), nullable=False, default="shared_db")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)