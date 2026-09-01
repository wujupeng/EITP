"""CertStatus 枚举 - 认证证书状态。"""

from __future__ import annotations

from enum import Enum


class CertStatus(str, Enum):
    DRAFT = "draft"
    SIGNED = "signed"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"