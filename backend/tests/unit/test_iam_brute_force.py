"""EITP-IAM-001 暴力破解防护服务单元测试。"""

from __future__ import annotations

import pytest

from app.infrastructure.audit import brute_force_service as bf_module
from app.infrastructure.audit.brute_force_service import BruteForceService


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, tuple[object, float | None]] = {}
        self._now: float = 0.0

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def _alive(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        _, expiry = entry
        if expiry is not None and self._now >= expiry:
            del self._store[key]
            return False
        return True

    async def incr(self, key: str) -> int:
        entry = self._store.get(key)
        if entry is None or not self._alive(key):
            self._store[key] = (1, None)
            return 1
        value, expiry = entry
        value += 1
        self._store[key] = (value, expiry)
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        entry = self._store.get(key)
        if entry is None:
            return False
        value, _ = entry
        self._store[key] = (value, self._now + seconds)
        return True

    async def setex(self, key: str, seconds: int, value: object) -> None:
        self._store[key] = (value, self._now + seconds)

    async def exists(self, key: str) -> int:
        return 1 if self._alive(key) else 0

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def ping(self) -> bool:
        return True


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()

    async def _get_redis() -> _FakeRedis:
        return fake

    monkeypatch.setattr(bf_module, "get_redis", _get_redis)
    return fake


def _service() -> BruteForceService:
    return BruteForceService(
        max_attempts=5,
        lockout_minutes=15,
        ip_ban_threshold=20,
        ip_ban_minutes=60,
    )


class BruteForceServiceTest:
    async def test_account_counter_increment_below_threshold(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(4):
            locked, banned = await svc.record_failure("alice", "10.0.0.1")
            assert locked is False
            assert banned is False
        assert await svc.is_account_locked("alice") is False

    async def test_account_lock_at_threshold(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(4):
            await svc.record_failure("alice", "10.0.0.1")
        locked, banned = await svc.record_failure("alice", "10.0.0.1")
        assert locked is True
        assert await svc.is_account_locked("alice") is True

    async def test_ip_counter_increment_below_threshold(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(19):
            _, banned = await svc.record_failure("bob", "10.0.0.2")
            assert banned is False
        assert await svc.is_ip_banned("10.0.0.2") is False

    async def test_ip_ban_at_threshold(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(19):
            await svc.record_failure("bob", "10.0.0.2")
        locked, banned = await svc.record_failure("bob", "10.0.0.2")
        assert banned is True
        assert await svc.is_ip_banned("10.0.0.2") is True

    async def test_reset_account_on_success(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        await svc.record_failure("carol", "10.0.0.3")
        await svc.record_failure("carol", "10.0.0.3")
        await svc.reset_account("carol")
        assert await svc.is_account_locked("carol") is False
        locked, _ = await svc.record_failure("carol", "10.0.0.3")
        assert locked is False

    async def test_lock_expiry_auto_unlock(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(5):
            await svc.record_failure("dave", "10.0.0.4")
        assert await svc.is_account_locked("dave") is True
        fake_redis.advance(15 * 60 + 1)
        assert await svc.is_account_locked("dave") is False

    async def test_ip_ban_expiry(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(20):
            await svc.record_failure("eve", "10.0.0.5")
        assert await svc.is_ip_banned("10.0.0.5") is True
        fake_redis.advance(60 * 60 + 1)
        assert await svc.is_ip_banned("10.0.0.5") is False

    async def test_independent_accounts(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(5):
            await svc.record_failure("frank", "10.0.0.6")
        assert await svc.is_account_locked("frank") is True
        assert await svc.is_account_locked("grace") is False

    async def test_independent_ips(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        for _ in range(20):
            await svc.record_failure("heidi", "10.0.0.7")
        assert await svc.is_ip_banned("10.0.0.7") is True
        assert await svc.is_ip_banned("10.0.0.8") is False

    async def test_record_failure_returns_tuple(self, fake_redis: _FakeRedis) -> None:
        svc = _service()
        result = await svc.record_failure("ivan", "10.0.0.9")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is False
        assert result[1] is False

    async def test_default_thresholds(self, fake_redis: _FakeRedis) -> None:
        svc = BruteForceService()
        for _ in range(4):
            locked, _ = await svc.record_failure("judy", "10.0.0.10")
            assert locked is False
        locked, _ = await svc.record_failure("judy", "10.0.0.10")
        assert locked is True