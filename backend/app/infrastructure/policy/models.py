"""IAM Policy ORM 模型。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PasswordPolicyORM(Base):
    __tablename__ = "iam_password_policy"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True, index=True)
    min_length: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    required_char_categories: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    history_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    expire_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    expire_grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    lockout_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    ip_ban_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    ip_ban_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordHistoryORM(Base):
    __tablename__ = "iam_password_history"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())