"""FeatureSwitchAggregate - 功能开关聚合根，封装模块级 + 子功能级两层粒度与父子继承。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import FeatureScope
from app.domain.biz_ops.value_objects.ids import FeatureKey
from app.domain.config.feature_flag import FeatureFlag
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class FeatureSwitchAggregate(AggregateRoot):
    """功能开关聚合根 - 两层粒度（模块级 / 子功能级）与父子继承。

    不变量：
    - 模块级开关关闭时，所有子功能级 effective_is_enabled 强制为 false
    - 模块级开关开启时，子功能级可独立配置
    - feature_key 格式: 模块级为 "module"，子功能级为 "module.sub_feature"
    - scope 与 parent_feature_key 一致性：SUB_FEATURE 必须有 parent，MODULE 不能有 parent
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        feature_key: str,
        scope: FeatureScope,
        is_enabled: bool,
        parent_feature_key: str | None = None,
        description: str | None = None,
        updated_by: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._feature_key = feature_key
        self._scope = scope
        self._is_enabled = is_enabled
        self._parent_feature_key = parent_feature_key
        self._description = description
        self._updated_by = updated_by
        self._updated_at = datetime.now(timezone.utc)
        self.validate()

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def feature_key(self) -> str:
        return self._feature_key

    @property
    def scope(self) -> FeatureScope:
        return self._scope

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @property
    def parent_feature_key(self) -> str | None:
        return self._parent_feature_key

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def updated_by(self) -> UUID | None:
        return self._updated_by

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def toggle(self, enabled: bool, updated_by: UUID) -> FeatureSwitchAggregate:
        """切换开关状态 - 返回新实例。"""
        return FeatureSwitchAggregate(
            id=self._id,
            tenant_id=self._tenant_id,
            feature_key=self._feature_key,
            scope=self._scope,
            is_enabled=enabled,
            parent_feature_key=self._parent_feature_key,
            description=self._description,
            updated_by=updated_by,
        )

    def resolve_effective(self, parent: FeatureSwitchAggregate | None) -> bool:
        """解析有效开关状态 - 模块级关闭时子功能级强制 false。"""
        if self._scope == FeatureScope.SUB_FEATURE and parent is not None:
            if not parent.is_enabled:
                return False
        return self._is_enabled

    def to_feature_flag(self) -> FeatureFlag:
        """转换为 FeatureFlag 值对象（复用现有 config 层）。"""
        return FeatureFlag(
            tenant_id=self._tenant_id,
            feature_key=self._feature_key,
            enabled=self._is_enabled,
        )

    def validate(self) -> None:
        """校验聚合根不变量。"""
        fk = FeatureKey.of(self._feature_key)

        if self._scope == FeatureScope.MODULE:
            if not fk.is_module_level():
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_KEY_FORMAT_INVALID,
                    f"模块级开关 feature_key 不能含 '.': {self._feature_key}",
                )
            if self._parent_feature_key is not None:
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_SCOPE_MISMATCH,
                    "模块级开关不能有 parent_feature_key",
                )
        elif self._scope == FeatureScope.SUB_FEATURE:
            if fk.is_module_level():
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_KEY_FORMAT_INVALID,
                    f"子功能级开关 feature_key 必须含 '.': {self._feature_key}",
                )
            expected_parent = fk.parent()
            if expected_parent is None:
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_SCOPE_MISMATCH,
                    f"子功能级开关无法解析 parent: {self._feature_key}",
                )
            if self._parent_feature_key is not None and self._parent_feature_key != expected_parent.value:
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_SCOPE_MISMATCH,
                    f"parent_feature_key({self._parent_feature_key}) 与 feature_key 解析的 parent({expected_parent.value}) 不一致",
                )