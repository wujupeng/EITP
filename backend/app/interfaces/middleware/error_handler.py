"""统一异常处理与错误码体系 - EITP_MT_* 前缀。"""

from __future__ import annotations

from enum import Enum

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from structlog import get_logger

logger = get_logger(__name__)


class ErrorCode(str, Enum):
    """EITP 错误码枚举 - 全部以 EITP_MT_ 前缀。"""

    # 租户上下文 (C-ISO-01)
    TENANT_CONTEXT_INVALID = "EITP_MT_TENANT_CONTEXT_INVALID"

    # 租户开通 (5.2.3)
    TENANT_ALREADY_EXISTS = "EITP_MT_TENANT_ALREADY_EXISTS"
    PROVISION_FAILED = "EITP_MT_PROVISION_FAILED"
    DEPROVISION_CONFIRM_REQUIRED = "EITP_MT_DEPROVISION_CONFIRM_REQUIRED"
    DEPROVISION_REQUIRES_DISABLE = "EITP_MT_DEPROVISION_REQUIRES_DISABLE"

    # 层级模型 (5.1.3)
    HIERARCHY_DEPTH_EXCEEDED = "EITP_MT_HIERARCHY_DEPTH_EXCEEDED"
    HIERARCHY_CROSS_TENANT = "EITP_MT_HIERARCHY_CROSS_TENANT"
    HIERARCHY_CIRCULAR_REF = "EITP_MT_HIERARCHY_CIRCULAR_REF"
    HIERARCHY_HAS_ACTIVE_DATA = "EITP_MT_HIERARCHY_HAS_ACTIVE_DATA"

    # 租户隔离 (5.3.3)
    CROSS_TENANT_REF_DENIED = "EITP_MT_CROSS_TENANT_REF_DENIED"

    # 配置 (5.4.3)
    CONFIG_INVALID = "EITP_MT_CONFIG_INVALID"
    CONFIG_INHERIT_CONFLICT = "EITP_MT_CONFIG_INHERIT_CONFLICT"
    FEATURE_HAS_ACTIVE_DATA = "EITP_MT_FEATURE_HAS_ACTIVE_DATA"

    # 业务规则 (5.5.3)
    WORKFLOW_INCOMPLETE = "EITP_MT_WORKFLOW_INCOMPLETE"

    # 集团模式 (5.6.3)
    GROUP_READONLY_VIOLATION = "EITP_MT_GROUP_READONLY_VIOLATION"
    GROUP_SNAPSHOT_DELAYED = "EITP_MT_GROUP_SNAPSHOT_DELAYED"
    MASTER_DATA_CONFLICT = "EITP_MT_MASTER_DATA_CONFLICT"
    MASTER_PROPAGATE_FAILED = "EITP_MT_MASTER_PROPAGATE_FAILED"
    SUBSIDIARY_ISOLATION_VIOLATION = "EITP_MT_SUBSIDIARY_ISOLATION_VIOLATION"

    # 主数据层级继承 (5.9.3)
    MASTER_BASE_READONLY = "EITP_MT_MASTER_BASE_READONLY"
    MASTER_ATTR_CONFLICT = "EITP_MT_MASTER_ATTR_CONFLICT"
    MASTER_NOT_FOUND = "EITP_MT_MASTER_NOT_FOUND"

    # 数据放置与迁移 (5.7.3)
    MIGRATION_IN_PROGRESS = "EITP_MT_MIGRATION_IN_PROGRESS"
    MIGRATION_VERIFY_FAILED = "EITP_MT_MIGRATION_VERIFY_FAILED"
    MIGRATION_TIMEOUT = "EITP_MT_MIGRATION_TIMEOUT"
    PLACEMENT_UNSUPPORTED = "EITP_MT_PLACEMENT_UNSUPPORTED"
    PLACEMENT_RESOURCE_INSUFFICIENT = "EITP_MT_PLACEMENT_RESOURCE_INSUFFICIENT"

    # 备份与恢复 (5.8.3)
    BACKUP_INTEGRITY_FAILED = "EITP_MT_BACKUP_INTEGRITY_FAILED"
    BACKUP_CORRUPTED = "EITP_MT_BACKUP_CORRUPTED"
    BACKUP_STORAGE_INSUFFICIENT = "EITP_MT_BACKUP_STORAGE_INSUFFICIENT"
    RESTORE_FAILED = "EITP_MT_RESTORE_FAILED"
    CROSS_TENANT_RESTORE_DENIED = "EITP_MT_CROSS_TENANT_RESTORE_DENIED"


class DomainError(Exception):
    """领域错误基类。"""

    def __init__(self, code: ErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TenantContextError(DomainError):
    def __init__(self, message: str = "租户上下文无效或缺失") -> None:
        super().__init__(ErrorCode.TENANT_CONTEXT_INVALID, message)


class HierarchyError(DomainError):
    pass


class ConfigError(DomainError):
    pass


class GroupError(DomainError):
    pass


def setup_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning(
            "domain_error",
            error_code=exc.code.value,
            message=exc.message,
            path=request.url.path,
            trace_id=getattr(request.state, "trace_id", None),
        )
        status = _status_for_code(exc.code)
        return JSONResponse(
            status_code=status,
            content={
                "error_code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_error",
            path=request.url.path,
            trace_id=getattr(request.state, "trace_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "EITP_MT_INTERNAL_ERROR",
                "message": "内部服务器错误",
            },
        )


def _status_for_code(code: ErrorCode) -> int:
    if code in {ErrorCode.TENANT_CONTEXT_INVALID, ErrorCode.CROSS_TENANT_REF_DENIED}:
        return 401 if code == ErrorCode.TENANT_CONTEXT_INVALID else 403
    if code == ErrorCode.TENANT_ALREADY_EXISTS:
        return 409
    if code in {
        ErrorCode.HIERARCHY_DEPTH_EXCEEDED,
        ErrorCode.HIERARCHY_CROSS_TENANT,
        ErrorCode.HIERARCHY_CIRCULAR_REF,
        ErrorCode.HIERARCHY_HAS_ACTIVE_DATA,
        ErrorCode.CONFIG_INVALID,
        ErrorCode.CONFIG_INHERIT_CONFLICT,
        ErrorCode.FEATURE_HAS_ACTIVE_DATA,
        ErrorCode.WORKFLOW_INCOMPLETE,
        ErrorCode.DEPROVISION_REQUIRES_DISABLE,
        ErrorCode.MASTER_DATA_CONFLICT,
        ErrorCode.MASTER_PROPAGATE_FAILED,
        ErrorCode.SUBSIDIARY_ISOLATION_VIOLATION,
        ErrorCode.MASTER_BASE_READONLY,
        ErrorCode.MASTER_ATTR_CONFLICT,
        ErrorCode.MASTER_NOT_FOUND,
        ErrorCode.MIGRATION_VERIFY_FAILED,
        ErrorCode.MIGRATION_TIMEOUT,
        ErrorCode.PLACEMENT_RESOURCE_INSUFFICIENT,
    }:
        return 422
    if code == ErrorCode.DEPROVISION_CONFIRM_REQUIRED:
        return 400
    if code == ErrorCode.GROUP_READONLY_VIOLATION:
        return 403
    if code == ErrorCode.CROSS_TENANT_RESTORE_DENIED:
        return 403
    if code == ErrorCode.GROUP_SNAPSHOT_DELAYED:
        return 200
    return 400