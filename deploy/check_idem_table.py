"""检查 idempotency 表结构。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine

async def check():
    f = get_session_factory()
    async with f() as s:
        r = await s.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'inv_idempotency_record' ORDER BY ordinal_position"))
        cols = [(row[0], row[1]) for row in r.fetchall()]
        print(f"inv_idempotency_record columns: {len(cols)}")
        for name, dtype in cols:
            print(f"  {name}: {dtype}")
    await close_engine()

asyncio.run(check())