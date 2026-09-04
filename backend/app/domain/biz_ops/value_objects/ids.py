"""BIZ-OPS 强类型 ID 值对象。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class FeatureKey:
    """功能开关键 - 格式: module.sub_feature 或 module。"""
    value: str

    @classmethod
    def of(cls, value: str) -> FeatureKey:
        return cls(value=value)

    def is_module_level(self) -> bool:
        return "." not in self.value

    def parent(self) -> FeatureKey | None:
        if "." not in self.value:
            return None
        return FeatureKey(self.value.rsplit(".", 1)[0])

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RuleKey:
    """业务规则键 - 租户内唯一。"""
    value: str

    @classmethod
    def of(cls, value: str) -> RuleKey:
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FlowKey:
    """审批流键。"""
    value: str

    @classmethod
    def of(cls, value: str) -> FlowKey:
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StrategyKey:
    """策略键。"""
    value: str

    @classmethod
    def of(cls, value: str) -> StrategyKey:
        return cls(value=value)

    def __str__(self) -> str:
        return self.value