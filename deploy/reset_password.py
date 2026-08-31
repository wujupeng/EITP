"""重置管理员密码以进行黄金链路验证。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine
from argon2 import PasswordHasher

NEW_PASSWORD = "Verify@2026!"

async def reset():
    f = get_session_factory()
    async with f() as s:
        ph = PasswordHasher()
        new_hash = ph.hash(NEW_PASSWORD)
        r = await s.execute(
            text("UPDATE iam_user SET password_hash = :h WHERE username = 'admin' RETURNING username"),
            {"h": new_hash},
        )
        row = r.fetchone()
        if row:
            print(f"Password reset for user: {row[0]}")
            print(f"New password: {NEW_PASSWORD}")
        else:
            print("admin user not found")
        await s.commit()
    await close_engine()

asyncio.run(reset())