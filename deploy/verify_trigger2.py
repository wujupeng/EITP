"""验证 Trigger 存在。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine

async def verify():
    f = get_session_factory()
    async with f() as s:
        r = await s.execute(text("SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_inv_%' ORDER BY tgname"))
        triggers = [row[0] for row in r.fetchall()]
        print(f"Triggers found: {len(triggers)}")
        for t in triggers:
            print(f"  {t}")
    await close_engine()

asyncio.run(verify())