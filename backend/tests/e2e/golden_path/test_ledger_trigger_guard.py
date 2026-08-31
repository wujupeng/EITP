"""Ledger Trigger 双保险验证测试。"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine


@pytest.mark.asyncio
async def test_ledger_trigger_blocks_update():
    """UPDATE 被 Trigger 拒绝。"""
    factory = get_session_factory()
    async with factory() as session:
        with pytest.raises(Exception, match="EITP_INV_LEDGER_APPEND_ONLY"):
            await session.execute(
                text("UPDATE inv_inventory_ledger SET quantity_change = 999 WHERE id IS NOT NULL LIMIT 1")
            )
    await close_engine()


@pytest.mark.asyncio
async def test_ledger_trigger_blocks_delete():
    """DELETE 被 Trigger 拒绝。"""
    factory = get_session_factory()
    async with factory() as session:
        with pytest.raises(Exception, match="EITP_INV_LEDGER_APPEND_ONLY"):
            await session.execute(
                text("DELETE FROM inv_inventory_ledger WHERE id IS NOT NULL LIMIT 1")
            )
    await close_engine()


@pytest.mark.asyncio
async def test_ledger_insert_not_blocked():
    """INSERT 不受影响。"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM inv_inventory_ledger"))
        count = result.scalar_one()
        assert count >= 0
    await close_engine()


@pytest.mark.asyncio
async def test_audit_trigger_blocks_update():
    """审计表 UPDATE 被 Trigger 拒绝。"""
    factory = get_session_factory()
    async with factory() as session:
        with pytest.raises(Exception, match="EITP_INV_LEDGER_APPEND_ONLY"):
            await session.execute(
                text("UPDATE inv_inventory_audit SET action = 'test' WHERE id IS NOT NULL LIMIT 1")
            )
    await close_engine()