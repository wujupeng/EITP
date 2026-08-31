"""余额快照校验器 - 定期校验余额快照与账本聚合一致性。"""

from __future__ import annotations

from structlog import get_logger

logger = get_logger(__name__)


class BalanceSnapshotValidator:
    """定期校验余额快照与账本聚合一致性。

    不一致时以账本聚合修复快照并告警。
    """

    async def validate_and_repair(
        self,
        balance_on_hand: float,
        ledger_total: float,
    ) -> tuple[bool, float]:
        if abs(balance_on_hand - ledger_total) < 0.0001:
            return True, balance_on_hand
        logger.warning(
            "balance_snapshot_inconsistent",
            balance_on_hand=balance_on_hand,
            ledger_total=ledger_total,
        )
        return False, ledger_total