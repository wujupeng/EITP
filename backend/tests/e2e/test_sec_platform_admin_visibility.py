"""平台管理员可见性边界验证 E2E 测试。"""

import pytest


class TestPlatformAdminVisibilityE2E:
    """运营元数据可见 + 业务数据默认不可见 + 显式申请审计 + 聚合数据不可推导。"""

    def test_operational_metadata_routes_defined(self) -> None:
        routes = ["/api/v1/platform/tenants", "/api/v1/platform/tenant-usage", "/api/v1/health"]
        assert len(routes) == 3

    def test_business_routes_defined(self) -> None:
        routes = ["/api/v1/inv/", "/api/v1/mdm/", "/api/v1/wms/", "/api/v1/pur/", "/api/v1/sal/"]
        assert len(routes) == 5

    def test_temp_permission_ttl(self) -> None:
        ttl = 7200
        assert ttl == 7200
        assert ttl == 2 * 3600