"""验证管理员密码。"""
import asyncio
from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory, close_engine
from argon2.low_level import verify_secret

PASSWORDS = [
    "Admin123!@#change",
    "Admin@2024!",
    "admin",
    "Admin123",
    "Admin123!@#",
    "Eitp@2024!",
    "ChangeMe123!",
]

async def verify():
    f = get_session_factory()
    async with f() as s:
        r = await s.execute(text("SELECT username, password_hash FROM iam_user WHERE username = 'admin' LIMIT 1"))
        row = r.fetchone()
        if not row:
            print("admin user not found")
            return
        print(f"username={row[0]}, hash={row[1]}")
        for pwd in PASSWORDS:
            try:
                ok = verify_secret(
                    pwd.encode(),
                    row[1].encode(),
                    type=2,
                )
                if ok:
                    print(f"  MATCH: password = {pwd}")
                    return
            except Exception:
                pass
        print("  No match found among tried passwords")
    await close_engine()

asyncio.run(verify())