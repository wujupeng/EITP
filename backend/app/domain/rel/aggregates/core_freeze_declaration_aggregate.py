"""REL Core Freeze 冻结声明聚合根 - CoreFreezeDeclarationAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.rel.enums import DeclarationStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class CoreFreezeDeclarationAggregate:
    """冻结声明聚合根 - DRAFT→EFFECTIVE 不可回退；EFFECTIVE 不可修改基线。"""

    declaration_id: UUID
    release_id: UUID
    freeze_scope: list[str]
    freeze_time: datetime
    freeze_baseline_hash: str
    unfreeze_process_definition: dict
    subsequent_milestone_rules: dict
    declaration_status: DeclarationStatus = DeclarationStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        release_id: UUID,
        freeze_scope: list[str],
        freeze_baseline_hash: str,
        unfreeze_process_definition: dict | None = None,
        subsequent_milestone_rules: dict | None = None,
    ) -> CoreFreezeDeclarationAggregate:
        return cls(
            declaration_id=uuid4(),
            release_id=release_id,
            freeze_scope=freeze_scope,
            freeze_time=datetime.now(timezone.utc),
            freeze_baseline_hash=freeze_baseline_hash,
            unfreeze_process_definition=unfreeze_process_definition or {},
            subsequent_milestone_rules=subsequent_milestone_rules or {},
        )

    def declare_effective(self) -> CoreFreezeDeclarationAggregate:
        if self.declaration_status != DeclarationStatus.DRAFT:
            raise RELError(
                RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE,
                f"only DRAFT can transition to EFFECTIVE, current={self.declaration_status.value}",
            )
        return replace(
            self,
            declaration_status=DeclarationStatus.EFFECTIVE,
            updated_at=datetime.now(timezone.utc),
        )

    def revoke(self) -> CoreFreezeDeclarationAggregate:
        if self.declaration_status != DeclarationStatus.EFFECTIVE:
            raise RELError(
                RELErrorCode.UNFREEZE_FORBIDDEN,
                f"only EFFECTIVE can be revoked, current={self.declaration_status.value}",
            )
        return replace(
            self,
            declaration_status=DeclarationStatus.REVOKED,
            updated_at=datetime.now(timezone.utc),
        )