"""配置版本聚合根 - 配置中心核心。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ConfigNamespace(str, Enum):
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    MODULE = "MODULE"


class ConfigValueType(str, Enum):
    STRING = "STRING"
    INT = "INT"
    FLOAT = "FLOAT"
    BOOL = "BOOL"
    JSON = "JSON"
    SECRET = "SECRET"


@dataclass(frozen=True)
class ConfigRevisionAggregate:
    """配置版本聚合根 - 版本化配置管理 + 灰度发布。"""

    revision_id: UUID
    namespace: str
    namespace_id: str | None
    config_key: str
    config_value: dict
    value_type: str
    description: str
    value_range: dict | None
    version: int
    changed_by: str
    changed_at: datetime
    gray_release_config: dict | None

    @classmethod
    def create(
        cls,
        namespace: str,
        config_key: str,
        config_value: dict,
        value_type: str,
        description: str,
        changed_by: str,
        namespace_id: str | None = None,
        version: int = 1,
        value_range: dict | None = None,
        gray_release_config: dict | None = None,
    ) -> ConfigRevisionAggregate:
        return cls(
            revision_id=uuid4(),
            namespace=namespace,
            namespace_id=namespace_id,
            config_key=config_key,
            config_value=config_value,
            value_type=value_type,
            description=description,
            value_range=value_range,
            version=version,
            changed_by=changed_by,
            changed_at=datetime.now(timezone.utc),
            gray_release_config=gray_release_config,
        )

    def is_secret(self) -> bool:
        return self.value_type == ConfigValueType.SECRET.value

    def is_gray_release(self) -> bool:
        return self.gray_release_config is not None