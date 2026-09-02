"""Core Freeze 冻结声明发布器 - CoreFreezeDeclarationIssuer。"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from structlog import get_logger

from app.domain.rel.aggregates.core_freeze_declaration_aggregate import (
    CoreFreezeDeclarationAggregate,
)
from app.domain.rel.enums import DeclarationStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.core_freeze_declaration_repository import (
    CoreFreezeDeclarationRepository,
)

logger = get_logger(__name__)

_FROZEN_MILESTONES = [
    "MT-001", "IAM-001", "INV-001", "MDM-001", "WMS-001",
    "PUR-001", "SAL-001", "SEC-001", "PLT-001", "PROD-001",
]


class CoreFreezeDeclarationIssuer:
    """冻结声明发布器 - 采集核心指纹 + 发布永久冻结声明。"""

    def __init__(
        self,
        declaration_repository: CoreFreezeDeclarationRepository,
        core_freeze_guard: object | None = None,
    ) -> None:
        self._declaration_repo = declaration_repository
        self._core_freeze_guard = core_freeze_guard

    async def issue_declaration(
        self,
        release_id: UUID,
    ) -> CoreFreezeDeclarationAggregate:
        fingerprints = {}
        if self._core_freeze_guard is not None:
            fingerprints = await self._core_freeze_guard.collect_fingerprints()

        baseline_content = json.dumps(fingerprints, sort_keys=True)
        baseline_hash = hashlib.sha256(baseline_content.encode()).hexdigest()

        declaration = CoreFreezeDeclarationAggregate.create(
            release_id=release_id,
            freeze_scope=_FROZEN_MILESTONES,
            freeze_baseline_hash=baseline_hash,
            unfreeze_process_definition={
                "process": "unfreeze_approval",
                "requires": ["release_manager_approval", "security_officer_approval", "cto_approval"],
                "steps": [
                    "1. 提交解冻申请（UNFREEZE_REQUESTED）",
                    "2. 发布经理审批",
                    "3. 安全负责人审批",
                    "4. CTO 审批",
                    "5. 执行解冻（REVOKED）",
                ],
            },
            subsequent_milestone_rules={
                "allowed": ["新增 Bounded Context", "新增 rel_* 表", "扩展 error_handler.py", "扩展 audit_entry.py"],
                "forbidden": ["修改已冻结聚合根", "修改已冻结 API 契约", "修改已冻结表结构", "修改已冻结 RLS 策略"],
                "freeze_type": "PERMANENT",
            },
        )

        declaration = declaration.declare_effective()
        await self._declaration_repo.save(declaration)
        await self._declaration_repo.update_to_effective(declaration.declaration_id)

        logger.info(
            "core_freeze_declaration_effective",
            release_id=str(release_id),
            declaration_id=str(declaration.declaration_id),
            baseline_hash=baseline_hash,
        )
        return declaration

    async def get_declaration(
        self,
        release_id: UUID,
    ) -> dict | None:
        return await self._declaration_repo.get_by_release(release_id)