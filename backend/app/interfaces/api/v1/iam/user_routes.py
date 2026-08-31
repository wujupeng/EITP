"""IAM 用户管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.iam.user_app_svc import UserAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode
from app.interfaces.schemas.iam import UserCreateRequest, UserResponse

router = APIRouter(prefix="/iam/users", tags=["iam-user"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    req: UserCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """创建用户。"""
    ctx = SecurityContext.current()
    if ctx is None:
        raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
    svc = UserAppSvc(session)
    user = await svc.create_user(
        tenant_id=ctx.tenant.tenant_id,
        username=req.username,
        password=req.password,
        email=req.email,
        phone=req.phone,
        real_name=req.real_name,
        is_tenant_admin=req.is_tenant_admin,
    )
    return UserResponse(
        id=user.id.value,
        username=user.username,
        email=user.email,
        phone=user.phone,
        real_name=user.real_name,
        account_status=user.account_status.value,
        is_tenant_admin=user.is_tenant_admin,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """列出租户内用户。"""
    ctx = SecurityContext.current()
    if ctx is None:
        raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
    svc = UserAppSvc(session)
    users = await svc.list_users(ctx.tenant.tenant_id, offset, limit)
    return [
        UserResponse(
            id=u.id.value,
            username=u.username,
            email=u.email,
            phone=u.phone,
            real_name=u.real_name,
            account_status=u.account_status.value,
            is_tenant_admin=u.is_tenant_admin,
        )
        for u in users
    ]


@router.patch("/{user_id}/disable")
async def disable_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """停用用户。"""
    svc = UserAppSvc(session)
    await svc.disable_user(user_id)
    return {"message": "用户已停用"}


@router.patch("/{user_id}/enable")
async def enable_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """启用用户。"""
    svc = UserAppSvc(session)
    await svc.enable_user(user_id)
    return {"message": "用户已启用"}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """管理员重置密码。"""
    svc = UserAppSvc(session)
    await svc.reset_password(user_id, body.get("new_password", ""))
    return {"message": "密码已重置"}
