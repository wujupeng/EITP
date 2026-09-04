"""TaxEngine - 税务计算引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.biz_ops.aggregates.tax_config_aggregate import TaxConfigAggregate
from app.domain.biz_ops.enums.enums import TaxDirection, TaxFlag, TaxType


@dataclass(frozen=True)
class TaxCalcLineResult:
    """单行税务计算结果。"""
    line_id: str
    tax_type: TaxType
    direction: TaxDirection
    tax_flag: TaxFlag
    base_amount: float
    tax_amount: float
    total_amount: float


@dataclass(frozen=True)
class TaxCalcResult:
    """税务计算结果。"""
    config_id: UUID
    config_key: str
    lines: tuple[TaxCalcLineResult, ...]
    total_tax: float
    total_amount: float

    @property
    def total_base(self) -> float:
        return sum(l.base_amount for l in self.lines)


class TaxEngine:
    """税务计算引擎 - 两层继承求值 → 多税种计算 → 进项/销项分类。"""

    def calculate(
        self,
        config: TaxConfigAggregate,
        lines: list[dict],
    ) -> TaxCalcResult:
        """计算税务。

        Args:
            config: 税务配置聚合根
            lines: 计算行列表，每行含 line_id, amount, tax_type(可选)
        Returns:
            TaxCalcResult 税务计算结果
        """
        if config.is_not_taxable() or config.is_exempt():
            return TaxCalcResult(
                config_id=config.id.value,
                config_key=config.config_key,
                lines=tuple(
                    TaxCalcLineResult(
                        line_id=l["line_id"], tax_type=TaxType(l.get("tax_type", "vat")),
                        direction=config.direction, tax_flag=config.tax_flag,
                        base_amount=l["amount"], tax_amount=0.0, total_amount=l["amount"],
                    )
                    for l in lines
                ),
                total_tax=0.0,
                total_amount=sum(l["amount"] for l in lines),
            )

        calc_lines: list[TaxCalcLineResult] = []
        total_tax = 0.0
        total_amount = 0.0

        for l in lines:
            tax_type = TaxType(l.get("tax_type", "vat"))
            rate = 0.0 if config.is_zero_rate() else config.get_default_rate(tax_type)
            amount = l["amount"]

            if config.tax_flag == TaxFlag.TAX_INCLUSIVE:
                base_amount = amount / (1 + rate) if (1 + rate) > 0 else amount
                tax_amount = amount - base_amount
                total = amount
            else:
                base_amount = amount
                tax_amount = amount * rate
                total = amount + tax_amount

            calc_lines.append(TaxCalcLineResult(
                line_id=l["line_id"], tax_type=tax_type, direction=config.direction,
                tax_flag=config.tax_flag, base_amount=base_amount,
                tax_amount=tax_amount, total_amount=total,
            ))
            total_tax += tax_amount
            total_amount += total

        return TaxCalcResult(
            config_id=config.id.value,
            config_key=config.config_key,
            lines=tuple(calc_lines),
            total_tax=total_tax,
            total_amount=total_amount,
        )