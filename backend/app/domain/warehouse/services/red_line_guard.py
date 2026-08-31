"""WMS 第一条红线防护 - 启动校验 WMS 服务账号对 inv_* 表无直接写权限。

红线：WMS = Physical Execution；INV = Inventory Truth。
WMS 不得直接修改 inv_inventory_ledger / inv_inventory_balance / inv_inventory_reservation，
必须通过 INV Transaction API 改变库存事实。

三重保证：
1. 启动校验（本模块）- 检查数据库权限
2. 代码审查清单 - 禁止 WMS 代码出现直接修改 inv_* 表的操作
3. RLS 策略 - WMS 服务账号对 inv_* 表 ENABLE RLS 且无 BYPASSRLS
"""

from __future__ import annotations

from structlog import get_logger

logger = get_logger(__name__)

PROTECTED_TABLES = [
    "inv_inventory_ledger",
    "inv_inventory_balance",
    "inv_inventory_reservation",
]

FORBIDDEN_PRIVILEGES = ["INSERT", "UPDATE", "DELETE"]

CODE_REVIEW_CHECKLIST = [
    "WMS 应用服务不得直接 import 或调用 inv_inventory_ledger / inv_inventory_balance / inv_inventory_reservation 的 ORM 模型",
    "WMS 仓储实现不得包含对 inv_* 表的 INSERT / UPDATE / DELETE SQL 语句",
    "WMS 作业执行必须通过 InventoryAppSvc.execute_transaction() 改变库存事实",
    "WMS 对账服务对 inv_* 表仅允许 SELECT（只读对账）",
    "WMS 领域事件不得直接触发 inv_* 表写入",
]


async def validate_red_line_on_startup(session_factory) -> bool:
    """启动时校验 WMS 服务账号对 inv_* 表无直接写权限。

    Args:
        session_factory: 异步数据库会话工厂

    Returns:
        True if validation passed, False otherwise.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    logger.info("wms_red_line_validation_start", protected_tables=PROTECTED_TABLES)

    violations: list[str] = []
    async with session_factory() as session:
        for table_name in PROTECTED_TABLES:
            result = await session.execute(
                text(
                    """
                    SELECT privilege_type
                    FROM information_schema.role_table_grants
                    WHERE table_name = :table_name
                      AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
                    """
                ),
                {"table_name": table_name},
            )
            rows = result.fetchall()
            for row in rows:
                violations.append(
                    f"WMS service account has {row[0]} privilege on {table_name}"
                )

    if violations:
        logger.error("wms_red_line_validation_failed", violations=violations)
        return False

    logger.info("wms_red_line_validation_passed")
    return True


def get_code_review_checklist() -> list[str]:
    """返回代码审查清单 - 禁止 WMS 代码直接修改 inv_* 表。"""
    return CODE_REVIEW_CHECKLIST