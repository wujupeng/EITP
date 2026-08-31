"""应用配置 - 基于 Pydantic Settings v2，环境变量注入与校验。"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EITP_",
        extra="ignore",
    )

    app_name: str = Field(default="EITP Multi-Tenant", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://eitp:eitp@localhost:5432/eitp",
        description="异步数据库连接 URL",
    )
    db_pool_size: int = Field(default=20, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=50)
    db_pool_recycle: int = Field(default=3600, ge=60)

    redis_url: str = Field(default="redis://localhost:6379/0")

    iam_base_url: str = Field(default="http://localhost:8081", description="IAM 服务地址")
    billing_base_url: str = Field(default="http://localhost:8082", description="计费服务地址")
    control_plane_url: str = Field(default="http://localhost:8090", description="控制面地址")

    tenant_context_cache_ttl: int = Field(default=300, ge=10, le=3600)
    feature_flag_cache_ttl: int = Field(default=60, ge=5, le=600)
    config_cache_ttl: int = Field(default=30, ge=5, le=300)

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    wms_putaway_strategy: str = Field(default="same_product_concentrate", description="上架策略")
    wms_picking_strategy: str = Field(default="fifo", description="拣货策略")
    wms_receiving_over_receive_ratio: float = Field(default=0.0, ge=0.0, description="收货超收比例（0=禁止超收）")
    wms_transfer_require_approval: bool = Field(default=True, description="移库是否需要审批")
    wms_reconcile_interval_seconds: int = Field(default=3600, ge=60, description="对账间隔（秒）")
    wms_task_auto_assign: bool = Field(default=False, description="Task 自动分配")
    wms_task_timeout_seconds: int = Field(default=7200, ge=60, description="Task 超时阈值（秒）")
    wms_batch_lot_enabled: bool = Field(default=False, description="批次/LOT 是否启用（P1）")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()