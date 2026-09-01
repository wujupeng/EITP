"""JoinLeakageTestExecutor - JOIN 跨租户泄露测试执行器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.infrastructure.sec.join_query_definition_registry import JoinQueryDefinition


@dataclass
class JoinLeakageResult:
    join_id: str
    is_isolated: bool = False
    total_rows: int = 0
    leaked_rows: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)


class JoinLeakageTestExecutor:
    """执行 JOIN 查询，验证结果集 tenant_id 一致。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client

    async def execute_join_test(
        self,
        join_def: JoinQueryDefinition,
        tenant_id: UUID,
    ) -> JoinLeakageResult:
        resp = await self._http_client.post(
            "/api/v1/sec/join-test",
            json={
                "left_table": join_def.left_table,
                "right_table": join_def.right_table,
                "join_condition": join_def.join_condition,
                "tenant_id": str(tenant_id),
            },
        )
        result = JoinLeakageResult(join_id=join_def.join_id)

        if resp.status_code == 200:
            data = resp.json()
            rows = data.get("rows", [])
            result.total_rows = len(rows)
            leaked = [r for r in rows if r.get("tenant_id") != str(tenant_id)]
            result.leaked_rows = len(leaked)
            result.is_isolated = result.leaked_rows == 0
            result.evidence = {"sql_plan": data.get("sql_plan", ""), "leaked_rows": leaked[:10]}
        else:
            result.is_isolated = False
            result.evidence = {"status": resp.status_code, "body": resp.text}

        return result

    async def execute_all_joins(
        self,
        join_defs: list[JoinQueryDefinition],
        tenant_id: UUID,
    ) -> list[JoinLeakageResult]:
        results: list[JoinLeakageResult] = []
        for jd in join_defs:
            result = await self.execute_join_test(jd, tenant_id)
            results.append(result)
        return results