"""RLSPolicyManager - 数据库层 RLS（Row Level Security）策略管理。

共享数据库模式：为所有业务表下发 RLS 策略，强制 tenant_id 隔离。
独立数据库/实例模式：禁用 RLS，靠连接隔离。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

logger = get_logger(__name__)


class PlacementMode(Enum):
    """数据库放置模式。"""

    SHARED_DB = "shared_db"
    DEDICATED_DB = "dedicated_db"
    DEDICATED_INSTANCE = "dedicated_instance"


class RLSPolicyManager:
    """RLS 策略管理器 - 按放置模式切换策略。"""

    def __init__(self, mode: PlacementMode = PlacementMode.SHARED_DB) -> None:
        self._mode = mode

    @property
    def mode(self) -> PlacementMode:
        return self._mode

    async def enable_rls_for_table(
        self,
        session: AsyncSession,
        table_name: str,
    ) -> None:
        """为指定表启用 RLS（仅共享数据库模式）。"""
        if self._mode != PlacementMode.SHARED_DB:
            logger.debug("RLS 跳过（非共享模式）", table=table_name, mode=self._mode.value)
            return

        await session.execute(text(f'ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY'))

        policy_name = f"rls_tenant_isolation_{table_name}"
        await session.execute(text(
            f"""
            CREATE OR REPLACE POLICY {policy_name} ON {table_name}
            USING (tenant_id = current_setting('app.tenant_id')::uuid)
            """
        ))
        logger.info("RLS 策略已启用", table=table_name, policy=policy_name)

    async def disable_rls_for_table(
        self,
        session: AsyncSession,
        table_name: str,
    ) -> None:
        """为指定表禁用 RLS。"""
        policy_name = f"rls_tenant_isolation_{table_name}"
        await session.execute(text(f'DROP POLICY IF EXISTS {policy_name} ON {table_name}'))
        await session.execute(text(f'ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY'))
        logger.info("RLS 策略已禁用", table=table_name)

    async def set_tenant_context(
        self,
        session: AsyncSession,
        tenant_id: Any,
    ) -> None:
        """设置当前连接的租户上下文（共享模式）。"""
        if self._mode != PlacementMode.SHARED_DB:
            return
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)},
        )

    async def clear_tenant_context(self, session: AsyncSession) -> None:
        """清除当前连接的租户上下文。"""
        if self._mode != PlacementMode.SHARED_DB:
            return
        await session.execute(text("SELECT set_config('app.tenant_id', '', false)"))

    def is_rls_active(self) -> bool:
        """RLS 是否在当前模式下生效。"""
        return self._mode == PlacementMode.SHARED_DB


class RLSPolicyProvider:
    """RLS 策略提供者接口 - 按放置模式创建对应的 RLSPolicyManager。"""

    @staticmethod
    def create(mode: PlacementMode) -> RLSPolicyManager:
        return RLSPolicyManager(mode=mode)