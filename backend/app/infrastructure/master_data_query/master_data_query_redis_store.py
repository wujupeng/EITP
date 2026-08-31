"""主数据查询 Redis 缓存仓储 - 集团商品目录/企业商品/条码定位缓存。

Redis 故障时降级为数据库查询（性能下降但功能不丢）。
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from structlog import get_logger

from app.infrastructure.cache.redis_client import (
    MDM_BARCODE_TTL,
    MDM_ENTERPRISE_PRODUCT_TTL,
    MDM_GROUP_PRODUCT_TTL,
    get_redis,
    mdm_barcode_key,
    mdm_enterprise_product_key,
    mdm_group_product_key,
)

logger = get_logger(__name__)


def _filter_hash(filter_dict: dict) -> str:
    """计算过滤条件哈希用于缓存键。"""
    raw = json.dumps(filter_dict, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


class MasterDataQueryRedisStore:
    """主数据查询 Redis 缓存仓储。

    集团商品目录查询缓存 TTL=300s，企业商品查询缓存 TTL=300s。
    """

    @staticmethod
    async def get_group_product_cache(filter_dict: dict) -> list[dict] | None:
        """获取集团商品目录查询缓存。"""
        try:
            r = await get_redis()
            key = mdm_group_product_key(_filter_hash(filter_dict))
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_group_product_cache_miss", exc_info=True)
            return None

    @staticmethod
    async def set_group_product_cache(filter_dict: dict, result: list[dict]) -> None:
        """设置集团商品目录查询缓存。"""
        try:
            r = await get_redis()
            key = mdm_group_product_key(_filter_hash(filter_dict))
            await r.set(key, json.dumps(result, default=str), ex=MDM_GROUP_PRODUCT_TTL)
        except Exception as e:
            logger.warning("redis_group_product_cache_set_failed", exc_info=True)

    @staticmethod
    async def get_enterprise_product_cache(tenant_id: UUID, filter_dict: dict) -> list[dict] | None:
        """获取企业商品查询缓存。"""
        try:
            r = await get_redis()
            key = mdm_enterprise_product_key(str(tenant_id), _filter_hash(filter_dict))
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_ep_cache_miss", exc_info=True)
            return None

    @staticmethod
    async def set_enterprise_product_cache(tenant_id: UUID, filter_dict: dict, result: list[dict]) -> None:
        """设置企业商品查询缓存。"""
        try:
            r = await get_redis()
            key = mdm_enterprise_product_key(str(tenant_id), _filter_hash(filter_dict))
            await r.set(key, json.dumps(result, default=str), ex=MDM_ENTERPRISE_PRODUCT_TTL)
        except Exception as e:
            logger.warning("redis_ep_cache_set_failed", exc_info=True)


class BarcodeLocatorRedisStore:
    """条码定位 Redis 缓存仓储。TTL=600s。"""

    @staticmethod
    async def get(tenant_id: UUID, barcode: str) -> dict | None:
        """通过条码定位 SKU（缓存）。"""
        try:
            r = await get_redis()
            key = mdm_barcode_key(str(tenant_id), barcode)
            data = await r.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_barcode_cache_miss", exc_info=True)
            return None

    @staticmethod
    async def set(tenant_id: UUID, barcode: str, result: dict) -> None:
        """设置条码定位缓存。"""
        try:
            r = await get_redis()
            key = mdm_barcode_key(str(tenant_id), barcode)
            await r.set(key, json.dumps(result, default=str), ex=MDM_BARCODE_TTL)
        except Exception as e:
            logger.warning("redis_barcode_cache_set_failed", exc_info=True)

    @staticmethod
    async def invalidate(tenant_id: UUID, barcode: str) -> None:
        """使条码缓存失效。"""
        try:
            r = await get_redis()
            key = mdm_barcode_key(str(tenant_id), barcode)
            await r.delete(key)
        except Exception as e:
            logger.warning("redis_barcode_cache_invalidate_failed", exc_info=True)