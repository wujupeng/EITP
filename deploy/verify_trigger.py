"""验证 Ledger Trigger 双保险生效。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine

async def verify():
    f = get_session_factory()
    async with f() as s:
        # Test 1: UPDATE should be blocked
        try:
            await s.execute(text("UPDATE inv_inventory_ledger SET quantity_change = 999 WHERE id IS NOT NULL LIMIT 1"))
            print("FAIL: UPDATE was not blocked by trigger!")
        except Exception as e:
            if "EITP_INV_LEDGER_APPEND_ONLY" in str(e):
                print("PASS: UPDATE blocked by trigger guard")
            else:
                print(f"UNEXPECTED: {type(e).__name__}: {str(e)[:100]}")

        # Test 2: DELETE should be blocked
        try:
            await s.execute(text("DELETE FROM inv_inventory_ledger WHERE id IS NOT NULL LIMIT 1"))
            print("FAIL: DELETE was not blocked by trigger!")
        except Exception as e:
            if "EITP_INV_LEDGER_APPEND_ONLY" in str(e):
                print("PASS: DELETE blocked by trigger guard")
            else:
                print(f"UNEXPECTED: {type(e).__name__}: {str(e)[:100]}")

        # Test 3: SELECT should work
        r = await s.execute(text("SELECT COUNT(*) FROM inv_inventory_ledger"))
        print(f"PASS: SELECT works, count={r.scalar_one()}")

    await close_engine()

asyncio.run(verify())