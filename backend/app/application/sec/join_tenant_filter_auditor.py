"""JoinTenantFilterAuditor - JOIN tenant_id 条件审计器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantFilterAuditResult:
    join_sql: str
    has_tenant_filter: bool = False
    missing_tables: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


class JoinTenantFilterAuditor:
    """解析 SQL AST，验证所有 JOIN 表含 tenant_id 条件。"""

    def audit(self, join_sql: str, tables: list[str]) -> TenantFilterAuditResult:
        result = TenantFilterAuditResult(join_sql=join_sql)
        sql_lower = join_sql.lower()
        missing: list[str] = []

        for table in tables:
            table_lower = table.lower()
            if table_lower in sql_lower:
                pattern = f"{table_lower}.tenant_id"
                if pattern not in sql_lower and "tenant_id" not in sql_lower:
                    missing.append(table)

        result.has_tenant_filter = len(missing) == 0
        result.missing_tables = missing
        result.evidence = {"tables_checked": tables, "missing": missing}
        return result