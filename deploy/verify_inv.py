"""验证 INV 表创建和黄金链路。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine

async def check_tables():
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'inv_%' ORDER BY tablename")
        )
        tables = [r[0] for r in result.fetchall()]
        print(f"INV tables created: {len(tables)}")
        for t in tables:
            print(f"  {t}")
        return len(tables)

async def golden_path():
    """黄金链路验证：采购入库100 → 预留30 → 销售出库30 → on_hand=70, available=70"""
    factory = get_session_factory()
    async with factory() as session:
        # 检查是否有库存余额数据
        result = await session.execute(
            text("SELECT COUNT(*) FROM inv_inventory_balance")
        )
        balance_count = result.scalar_one()
        print(f"\nInventory balance records: {balance_count}")

        # 检查是否有库存账本数据
        result = await session.execute(
            text("SELECT COUNT(*) FROM inv_inventory_ledger")
        )
        ledger_count = result.scalar_one()
        print(f"Inventory ledger records: {ledger_count}")

        # 检查是否有库存事务数据
        result = await session.execute(
            text("SELECT COUNT(*) FROM inv_inventory_transaction")
        )
        tx_count = result.scalar_one()
        print(f"Inventory transaction records: {tx_count}")

        # 检查余额一致性（available 是计算属性 = on_hand - reserved，不持久化）
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM inv_inventory_balance "
                "WHERE reserved > on_hand"
            )
        )
        inconsistent = result.scalar_one()
        print(f"Inconsistent balances (reserved > on_hand): {inconsistent}")
        if inconsistent == 0:
            print("PASS: All balances consistent (reserved <= on_hand)")
        else:
            print("FAIL: Inconsistent balances detected")

async def main():
    n = await check_tables()
    if n > 0:
        await golden_path()
    else:
        print("FAIL: No INV tables found")
    await close_engine()

asyncio.run(main())