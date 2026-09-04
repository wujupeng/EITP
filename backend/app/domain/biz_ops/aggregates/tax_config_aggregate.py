"""TaxConfigAggregate - 税务配置聚合根。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import TaxDirection, TaxFlag, TaxScopeLevel, TaxType
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


@dataclass(frozen=True)
class TaxRateEntry:
    """税率条目 - 单税种多税率。"""
    tax_type: TaxType
    rate: float
    is_default: bool = False


@dataclass(frozen=True)
class SpecialTaxRule:
    """特殊税务规则。"""
    rule: str
    description: str = ""


class TaxConfigAggregate(AggregateRoot):
    """税务配置聚合根 - 多税种多税率、含税不含税、进项销项、特殊规则。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        config_key: str,
        config_name: str,
        tax_rates: tuple[TaxRateEntry, ...],
        tax_flag: TaxFlag = TaxFlag.TAX_EXCLUSIVE,
        direction: TaxDirection = TaxDirection.OUTPUT,
        scope_level: TaxScopeLevel = TaxScopeLevel.TENANT,
        scope_ref: str | None = None,
        special_rules: tuple[SpecialTaxRule, ...] = (),
        is_active: bool = True,
        version: int = 1,
        description: str | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._config_key = config_key
        self._config_name = config_name
        self._tax_rates = tax_rates
        self._tax_flag = tax_flag
        self._direction = direction
        self._scope_level = scope_level
        self._scope_ref = scope_ref
        self._special_rules = special_rules
        self._is_active = is_active
        self._version = version
        self._description = description
        self.validate()

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def config_key(self) -> str: return self._config_key
    @property
    def config_name(self) -> str: return self._config_name
    @property
    def tax_rates(self) -> tuple[TaxRateEntry, ...]: return self._tax_rates
    @property
    def tax_flag(self) -> TaxFlag: return self._tax_flag
    @property
    def direction(self) -> TaxDirection: return self._direction
    @property
    def scope_level(self) -> TaxScopeLevel: return self._scope_level
    @property
    def scope_ref(self) -> str | None: return self._scope_ref
    @property
    def special_rules(self) -> tuple[SpecialTaxRule, ...]: return self._special_rules
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def version(self) -> int: return self._version
    @property
    def description(self) -> str | None: return self._description

    def get_default_rate(self, tax_type: TaxType) -> float:
        """获取指定税种的默认税率。"""
        for entry in self._tax_rates:
            if entry.tax_type == tax_type and entry.is_default:
                return entry.rate
        for entry in self._tax_rates:
            if entry.tax_type == tax_type:
                return entry.rate
        return 0.0

    def is_exempt(self) -> bool:
        """是否免税。"""
        return any(r.rule == "exempt" for r in self._special_rules)

    def is_zero_rate(self) -> bool:
        """是否零税率。"""
        return any(r.rule == "zero_rate" for r in self._special_rules)

    def is_not_taxable(self) -> bool:
        """是否不征税。"""
        return any(r.rule == "not_taxable" for r in self._special_rules)

    def validate_rate(self) -> None:
        """税率合法性校验 [0, 1]。"""
        for entry in self._tax_rates:
            if not (0 <= entry.rate <= 1):
                raise BizOpsError(
                    BizOpsErrorCode.TAX_CALCULATION_FAILED,
                    f"税率必须在 [0, 1] 范围内: {entry.tax_type.value} = {entry.rate}",
                )

    def validate(self) -> None:
        """配置完整性校验。"""
        if not self._config_key or len(self._config_key) > 100:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, "config_key 不能为空且不超过 100 字符")
        if not self._tax_rates:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, "至少需要一个税率条目")
        self.validate_rate()
        if self._scope_level == TaxScopeLevel.COMPANY and not self._scope_ref:
            raise BizOpsError(BizOpsErrorCode.TAX_CALCULATION_FAILED, "公司级配置必须指定 scope_ref")