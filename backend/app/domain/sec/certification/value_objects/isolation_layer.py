"""IsolationLayer / NineOperation / Conclusion 枚举 - 15 层 × 9 操作 × 3 态结论。"""

from __future__ import annotations

from enum import Enum


class IsolationLayer(str, Enum):
    JWT = "jwt"
    TENANT_TOKEN = "tenant_token"
    TENANT_CONTEXT = "tenant_context"
    DATA_SCOPE = "data_scope"
    API = "api"
    APPLICATION = "application"
    REPOSITORY = "repository"
    RLS = "rls"
    JOIN = "join"
    AGGREGATE = "aggregate"
    AUDIT = "audit"
    EXPORT = "export"
    CACHE = "cache"
    ASYNC_JOB = "async_job"
    E2E = "e2e"


class NineOperation(str, Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    JOIN = "join"
    AGGREGATE = "aggregate"
    COUNT = "count"
    EXPORT = "export"
    AUDIT = "audit"


class Conclusion(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    PASS = "pass"
    FAIL = "fail"
    UNEXECUTABLE = "unexecutable"