"""查询管理员用户信息。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine

async def q():
    f = get_session_factory()
    async with f() as s:
        # 先看表结构
        r = await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'iam_user' ORDER BY ordinal_position"))
        cols = [row[0] for row in r.fetchall()]
        print(f"iam_user columns: {cols}")

        # 查询 admin 用户
        r = await s.execute(text("SELECT username, password_hash FROM iam_user WHERE username = 'admin' LIMIT 1"))
        row = r.fetchone()
        if row:
            print(f"username={row[0]}, hash_prefix={row[1][:40]}...")
        else:
            print("admin user not found")
    await close_engine()

asyncio.run(q())
