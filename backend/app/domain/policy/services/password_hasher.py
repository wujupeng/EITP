"""Argon2id 密码哈希服务 - 加盐哈希与验证。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


@dataclass(frozen=True)
class HashResult:
    hash: str
    salt: str


class PasswordHashStrategy(Protocol):
    def hash(self, plain: str) -> HashResult: ...
    def verify(self, plain: str, hash: str, salt: str) -> bool: ...


class Argon2Hasher:
    """Argon2id 密码哈希服务。

    time_cost=3, memory_cost=64MB, parallelism=4
    盐值由 argon2-cffi 内部生成并嵌入哈希字符串中。
    """

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, plain: str) -> HashResult:
        h = self._hasher.hash(plain)
        parts = h.split("$")
        salt = parts[4] if len(parts) > 4 else ""
        return HashResult(hash=h, salt=salt)

    def verify(self, plain: str, hash: str, salt: str = "") -> bool:
        try:
            return self._hasher.verify(hash, plain)
        except VerifyMismatchError:
            return False
        except Exception:
            return False


class BcryptHasher:
    """bcrypt 降级哈希方案。"""

    def __init__(self) -> None:
        import bcrypt
        self._bcrypt = bcrypt

    def hash(self, plain: str) -> HashResult:
        salt = self._bcrypt.gensalt(rounds=12)
        h = self._bcrypt.hashpw(plain.encode(), salt).decode()
        return HashResult(hash=h, salt=salt.decode())

    def verify(self, plain: str, hash: str, salt: str = "") -> bool:
        try:
            return self._bcrypt.checkpw(plain.encode(), hash.encode())
        except Exception:
            return False


def get_password_hasher() -> PasswordHashStrategy:
    """获取密码哈希器（默认 Argon2id）。"""
    return Argon2Hasher()