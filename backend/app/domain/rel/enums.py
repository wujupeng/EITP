"""REL 枚举定义 - 封版状态/裁决/资产类型/门禁类型/声明状态/演练状态。"""

from __future__ import annotations

from enum import Enum


class SealStatus(str, Enum):
    REQUESTED = "REQUESTED"
    GATE_RUNNING = "GATE_RUNNING"
    GATE_FAILED = "GATE_FAILED"
    SNAPSHOT_COLLECTING = "SNAPSHOT_COLLECTING"
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    REPORT_ASSEMBLING = "REPORT_ASSEMBLING"
    PENDING_CO_SIGN = "PENDING_CO_SIGN"
    SEALED = "SEALED"
    FAILED = "FAILED"


class SealVerdict(str, Enum):
    FINAL_PASS = "FINAL_PASS"
    FINAL_FAIL = "FINAL_FAIL"


class AssetType(str, Enum):
    GIT_TAG = "GIT_TAG"
    MIGRATION_BASELINE = "MIGRATION_BASELINE"
    DDL_SNAPSHOT = "DDL_SNAPSHOT"
    OPENAPI = "OPENAPI"
    PERMISSION_MATRIX = "PERMISSION_MATRIX"
    RLS_BASELINE = "RLS_BASELINE"
    SEC_CERT = "SEC_CERT"
    PROD_DOSSIER = "PROD_DOSSIER"
    TEST_RESULT = "TEST_RESULT"
    PERF_CAPACITY_BASELINE = "PERF_CAPACITY_BASELINE"
    DOCKER_IMAGE_LOCK = "DOCKER_IMAGE_LOCK"
    CONFIG_BASELINE = "CONFIG_BASELINE"
    BACKUP_EVIDENCE = "BACKUP_EVIDENCE"
    DR_EVIDENCE = "DR_EVIDENCE"
    ROLLBACK_PLAN = "ROLLBACK_PLAN"


class GateType(str, Enum):
    MILESTONE_FINAL_PASS = "MILESTONE_FINAL_PASS"
    CORE_FREEZE_HASH = "CORE_FREEZE_HASH"
    REGRESSION_378 = "REGRESSION_378"
    GIT_CLEAN = "GIT_CLEAN"
    TAG_CONFLICT = "TAG_CONFLICT"
    CERT_VALIDITY = "CERT_VALIDITY"


class DeclarationStatus(str, Enum):
    DRAFT = "DRAFT"
    EFFECTIVE = "EFFECTIVE"
    REVOKED = "REVOKED"


class DrillStatus(str, Enum):
    NOT_DRILLED = "NOT_DRILLED"
    DRILLED_PASS = "DRILLED_PASS"
    DRILLED_FAIL = "DRILLED_FAIL"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"


_TERMINAL_STATES = frozenset({
    SealStatus.SEALED,
    SealStatus.GATE_FAILED,
    SealStatus.SNAPSHOT_FAILED,
    SealStatus.FAILED,
})

_VALID_TRANSITIONS: dict[SealStatus, frozenset[SealStatus]] = {
    SealStatus.REQUESTED: frozenset({SealStatus.GATE_RUNNING, SealStatus.FAILED}),
    SealStatus.GATE_RUNNING: frozenset({SealStatus.SNAPSHOT_COLLECTING, SealStatus.GATE_FAILED}),
    SealStatus.GATE_FAILED: frozenset(),
    SealStatus.SNAPSHOT_COLLECTING: frozenset({SealStatus.REPORT_ASSEMBLING, SealStatus.SNAPSHOT_FAILED}),
    SealStatus.SNAPSHOT_FAILED: frozenset(),
    SealStatus.REPORT_ASSEMBLING: frozenset({SealStatus.PENDING_CO_SIGN, SealStatus.FAILED}),
    SealStatus.PENDING_CO_SIGN: frozenset({SealStatus.SEALED, SealStatus.FAILED}),
    SealStatus.SEALED: frozenset(),
    SealStatus.FAILED: frozenset(),
}


def is_terminal(status: SealStatus) -> bool:
    return status in _TERMINAL_STATES


def is_valid_transition(current: SealStatus, target: SealStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, frozenset())