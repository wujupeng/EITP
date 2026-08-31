"""负库存策略聚合根 - 五种模式。"""

from __future__ import annotations

from uuid import UUID

from app.domain.inventory.value_objects.shared import NegativePolicyMode
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId


class NegativeStockPolicyAggregate(AggregateRoot):
    """负库存策略聚合根 - 五种模式。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        mode: NegativePolicyMode = NegativePolicyMode.GLOBAL_FORBID,
        allow_force: bool = False,
        require_approval: bool = False,
        approval_timeout_seconds: int = 3600,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._mode = mode
        self._allow_force = allow_force
        self._require_approval = require_approval
        self._approval_timeout_seconds = approval_timeout_seconds

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def mode(self) -> NegativePolicyMode:
        return self._mode

    @property
    def allow_force(self) -> bool:
        return self._allow_force

    @property
    def require_approval(self) -> bool:
        return self._require_approval

    @property
    def approval_timeout_seconds(self) -> int:
        return self._approval_timeout_seconds

    def is_negative_allowed(self) -> bool:
        return self._mode in (
            NegativePolicyMode.GLOBAL_ALLOW,
            NegativePolicyMode.BY_BUSINESS,
            NegativePolicyMode.BY_WAREHOUSE,
        )

    def can_force_negative(self, user_is_admin: bool) -> bool:
        return self._allow_force and user_is_admin

    def needs_approval(self) -> bool:
        return self._mode == NegativePolicyMode.REQUIRE_APPROVAL or self._require_approval