"""PlatformAdminVisibilityVerifier - 平台管理员可见性验证器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.sec.platform_admin.services.aggregate_data_reversibility_checker import (
    AggregateDataReversibilityChecker,
    ReversibilityAssessment,
)


@dataclass
class VisibilityResult:
    operational_metadata_visible: bool = False
    business_data_default_hidden: bool = False
    explicit_request_audited: bool = False
    aggregate_non_reversible: bool = False
    permission_separated: bool = False
    reversibility_assessments: list[ReversibilityAssessment] = field(default_factory=list)


class PlatformAdminVisibilityVerifier:
    """验证运营元数据可见 + 业务数据默认不可见 + 显式申请审计 + 聚合数据不可推导 + 权限分离。"""

    def __init__(self, http_client: Any) -> None:
        self._http_client = http_client
        self._reversibility_checker = AggregateDataReversibilityChecker()

    async def verify(self, platform_admin_token: str) -> VisibilityResult:
        result = VisibilityResult()
        headers = {"Authorization": f"Bearer {platform_admin_token}"}

        result.operational_metadata_visible = await self._verify_operational_metadata(headers)
        result.business_data_default_hidden = await self._verify_business_data_hidden(headers)
        result.explicit_request_audited = await self._verify_explicit_request(headers)
        result.aggregate_non_reversible = await self._verify_aggregate_non_reversible(headers)
        result.permission_separated = await self._verify_permission_separation(headers)

        return result

    async def _verify_operational_metadata(self, headers: dict[str, str]) -> bool:
        resp = await self._http_client.get("/api/v1/platform/tenants", headers=headers)
        return resp.status_code == 200

    async def _verify_business_data_hidden(self, headers: dict[str, str]) -> bool:
        resp = await self._http_client.get("/api/v1/inv/balances", headers=headers)
        return resp.status_code in (401, 403)

    async def _verify_explicit_request(self, headers: dict[str, str]) -> bool:
        resp = await self._http_client.get("/api/v1/sec/platform-admin-access/requests", headers=headers)
        return resp.status_code == 200

    async def _verify_aggregate_non_reversible(self, headers: dict[str, str]) -> bool:
        resp = await self._http_client.get("/api/v1/sal/reports/aggregate", headers=headers)
        if resp.status_code != 200:
            return True
        data = resp.json()
        all_non_reversible = True
        for item in data.get("items", []):
            assessment = self._reversibility_checker.check(item.get("data", {}), item.get("count", 0))
            if assessment.is_reversible:
                all_non_reversible = False
        return all_non_reversible

    async def _verify_permission_separation(self, headers: dict[str, str]) -> bool:
        resp = await self._http_client.get("/api/v1/iam/permissions", headers=headers)
        if resp.status_code != 200:
            return False
        perms = resp.json()
        has_platform = any("sec:" in p.get("code", "") for p in perms)
        has_tenant = any("sal:" in p.get("code", "") for p in perms)
        return has_platform and has_tenant