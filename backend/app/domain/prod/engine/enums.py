"""PROD 验证执行枚举定义。"""

from __future__ import annotations

from enum import Enum


class VerificationItem(str, Enum):
    """16 项验证项枚举。"""

    BASELINE = "V01_BASELINE"
    CONCURRENT = "V02_CONCURRENT"
    CONNPOOL = "V03_CONNPOOL"
    CACHE = "V04_CACHE"
    OUTBOX = "V05_OUTBOX"
    SAGA = "V06_SAGA"
    JOB = "V07_JOB"
    ALERT = "V08_ALERT"
    TRACE = "V09_TRACE"
    BACKUP = "V10_BACKUP"
    DR = "V11_DR"
    CONTAINER = "V12_CONTAINER"
    RATELIMIT = "V13_RATELIMIT"
    LARGE_TENANT = "V14_LARGE_TENANT"
    REGRESSION = "V15_REGRESSION"
    SEC_RECERT = "V16_SEC_RECERT"


class VerificationConclusion(str, Enum):
    """验证结论枚举。"""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationStatus(str, Enum):
    """验证执行状态机枚举。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    EVIDENCE_COLLECTING = "EVIDENCE_COLLECTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceType(str, Enum):
    """证据类型枚举 - 证据三元组。"""

    REPORT = "REPORT"
    METRICS_SNAPSHOT = "METRICS_SNAPSHOT"
    LOG = "LOG"


class VerificationEnvironment(str, Enum):
    """验证执行环境枚举 - 禁止 PROD。"""

    STAGING = "STAGING"
    PRE_PROD = "PRE_PROD"


class ExecutorRole(str, Enum):
    """验证执行人角色枚举。"""

    SRE = "SRE"
    PERF = "PERF"
    DBA = "DBA"
    SEC_OFF = "SEC_OFF"
    PA = "PA"
    CICD = "CICD"


class DossierStatus(str, Enum):
    """生产就绪证明书状态枚举。"""

    DRAFT = "DRAFT"
    PENDING_SIGN = "PENDING_SIGN"
    SIGNED = "SIGNED"
    INVALID = "INVALID"


class DossierVerdict(str, Enum):
    """证明书裁决枚举。"""

    READY = "READY"
    NOT_READY = "NOT_READY"
    CONDITIONAL = "CONDITIONAL"