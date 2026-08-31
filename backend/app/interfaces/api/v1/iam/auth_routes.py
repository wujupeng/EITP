"""IAM 认证路由 - 登录/登出/刷新/改密/me。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.iam.auth_app_svc import AuthAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.iam import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    RefreshTokenRequest,
)

router = APIRouter(prefix="/auth", tags=["iam-auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """用户登录。"""
    svc = AuthAppSvc(session)
    result = await svc.login(
        tenant_id=req.tenant_id,
        username=req.username,
        password=req.password,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("User-Agent", ""),
    )
    return LoginResponse(**result)


@router.post("/logout")
async def logout(
    req: LogoutRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """用户登出。"""
    auth_header = request.headers.get("Authorization", "")
    access_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    svc = AuthAppSvc(session)
    await svc.logout(access_token, req.refresh_token)
    return {"message": "已登出"}


@router.post("/refresh")
async def refresh_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """刷新 Access Token。"""
    svc = AuthAppSvc(session)
    return await svc.refresh(req.refresh_token)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """修改密码。"""
    ctx = SecurityContext.current()
    if ctx is None:
        from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode
        raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
    svc = AuthAppSvc(session)
    await svc.change_password(ctx.user.user_id, req.old_password, req.new_password)
    return {"message": "密码修改成功"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    """获取当前登录用户信息。"""
    ctx = SecurityContext.current()
    if ctx is None:
        from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode
        raise IAMError(IAMErrorCode.TOKEN_MISSING, "未认证")
    svc = AuthAppSvc(session)
    result = await svc.get_me(ctx.user.user_id)
    return MeResponse(**result)
