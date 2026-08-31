"""异步 Redis 客户端 - 承载 Token 撤销列表、暴力破解计数、Session 缓存、INV 幂等记录与余额快照、MDM 主数据缓存、WMS 库存位置与任务缓存。"""

from __future__ import annotations

from redis.asyncio import Redis, from_url
from structlog import get_logger

from app.config import get_settings

logger = get_logger(__name__)

IDEMPOTENCY_TTL = 604800
BALANCE_SNAPSHOT_TTL = 60
RESERVATION_EXPIRY_SCAN_INTERVAL = 300

MDM_GROUP_PRODUCT_TTL = 300
MDM_ENTERPRISE_PRODUCT_TTL = 300
MDM_BARCODE_TTL = 600
MDM_REFERENCE_TTL = 120

WMS_POSITION_TTL = 120
WMS_LOCATION_TTL = 300
WMS_TASK_IDEMPOTENCY_TTL = 86400

_redis: Redis | None = None


def idempotency_key(tenant_id: str, idempotency_key: str) -> str:
    return f"idem:{tenant_id}:{idempotency_key}"


def balance_key(tenant_id: str, warehouse_id: str, sku_id: str) -> str:
    return f"bal:{tenant_id}:{warehouse_id}:{sku_id}"


def mdm_group_product_key(filter_hash: str) -> str:
    return f"mdm:group_product:{filter_hash}"


def mdm_enterprise_product_key(tenant_id: str, filter_hash: str) -> str:
    return f"mdm:ep:{tenant_id}:{filter_hash}"


def mdm_barcode_key(tenant_id: str, barcode: str) -> str:
    return f"mdm:barcode:{tenant_id}:{barcode}"


def mdm_reference_key(tenant_id: str, group_product_id: str) -> str:
    return f"mdm:ref:{tenant_id}:{group_product_id}"


def wms_position_key(tenant_id: str, filter_hash: str) -> str:
    return f"wms:position:{tenant_id}:{filter_hash}"


def wms_location_key(tenant_id: str, location_code: str) -> str:
    return f"wms:location:{tenant_id}:{location_code}"


def wms_task_idempotency_key(tenant_id: str, idempotency_key: str) -> str:
    return f"wms:task:idem:{tenant_id}:{idempotency_key}"


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
            health_check_interval=30,
        )
        logger.info("redis_connected", url=settings.redis_url)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("redis_closed")


async def redis_health_check() -> bool:
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False