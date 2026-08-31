"""为现有租户创建初始 IAM 资源（管理员用户、内置角色、权限）。"""

import asyncio
import sys
sys.path.insert(0, "/home/debian/EITP/backend")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID

async def main():
    engine = create_async_engine("postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    tenant_id = UUID("03724bb5-fd4d-46e5-af21-c794b559d406")
    
    async with async_session() as session:
        from app.application.iam.iam_provisioning_svc import IamProvisioningSvc
        svc = IamProvisioningSvc(session)
        result = await svc.provision_tenant_iam(
            tenant_id=tenant_id,
            admin_username="admin",
            admin_password="Qk@2026#Secure99",
            admin_email="admin@qiankunzhi.com",
        )
        print("IAM Provisioning Result:")
        print(f"  Tenant ID: {result['tenant_id']}")
        print(f"  Admin User ID: {result['admin_user_id']}")
        print(f"  Admin Username: {result['admin_username']}")
        print(f"  Roles Created: {result['roles_created']}")
        print(f"  Permissions Created: {result['permissions_created']}")
        print()
        print("Login credentials:")
        print(f"  Tenant ID: {tenant_id}")
        print(f"  Username: admin")
        print(f"  Password: Admin@2026#secure")
    
    await engine.dispose()

asyncio.run(main())