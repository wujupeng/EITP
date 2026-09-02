"""生产就绪证明书签发器。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.prod.dossier.aggregates.production_readiness_dossier_aggregate import (
    ProductionReadinessDossierAggregate,
)
from app.domain.prod.engine.enums import DossierStatus
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError

logger = logging.getLogger(__name__)

DEFAULT_VALID_DAYS = 365


class DossierRepositoryProtocol:
    """证明书仓储接口。"""

    async def save(self, dossier: ProductionReadinessDossierAggregate) -> None: ...

    async def get_by_id(self, dossier_id: UUID) -> ProductionReadinessDossierAggregate | None: ...


class AuditWriterProtocol:
    """审计写入接口。"""

    async def write(self, entry: AuditEntry) -> None: ...


class RoleCheckerProtocol:
    """角色校验接口。"""

    async def is_security_officer(self, user_id: UUID) -> bool: ...


class DossierSigner:
    """生产就绪证明书签发器。

    校验签发人角色 → 记录签发信息 → 状态流转至 SIGNED → 审计
    """

    def __init__(
        self,
        dossier_repo: DossierRepositoryProtocol,
        role_checker: RoleCheckerProtocol,
        audit_writer: AuditWriterProtocol | None = None,
        valid_days: int = DEFAULT_VALID_DAYS,
    ) -> None:
        self._repo = dossier_repo
        self._role_checker = role_checker
        self._audit_writer = audit_writer
        self._valid_days = valid_days

    async def sign(
        self,
        dossier_id: UUID,
        signer_id: UUID,
        tenant_id: UUID,
    ) -> ProductionReadinessDossierAggregate:
        is_officer = await self._role_checker.is_security_officer(signer_id)
        if not is_officer:
            raise PRODError(
                PRODErrorCode.DOSSIER_UNAUTHORIZED_SIGNER,
                "签发人必须为安全负责人",
            )

        dossier = await self._repo.get_by_id(dossier_id)
        if dossier is None:
            raise PRODError(
                PRODErrorCode.DOSSIER_NOT_FOUND,
                f"证明书不存在: {dossier_id}",
            )

        if dossier.status == DossierStatus.SIGNED:
            raise PRODError(
                PRODErrorCode.DOSSIER_ALREADY_SIGNED,
                f"证明书已签发: {dossier_id}",
            )

        valid_until = datetime.now(timezone.utc) + timedelta(days=self._valid_days)
        signed_dossier = dossier.sign(signer=str(signer_id), valid_until=valid_until)
        await self._repo.save(signed_dossier)

        if self._audit_writer:
            entry = AuditEntry.create(
                tenant_id=tenant_id,
                user_id=signer_id,
                action=AuditAction.DOSSIER_SIGNED,
                entity_type="readiness_dossier",
                entity_id=str(signed_dossier.dossier_id),
                new_value={
                    "signer": str(signer_id),
                    "valid_until": valid_until.isoformat(),
                    "verdict": signed_dossier.verdict.value if signed_dossier.verdict else None,
                },
            )
            await self._audit_writer.write(entry)

        logger.info("Dossier signed: %s by %s", dossier_id, signer_id)
        return signed_dossier