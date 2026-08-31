"""JWT RS256 密钥管理 - 私钥仅 IAM 持有，公钥分发至所有校验方。

支持双公钥轮换期校验：新公钥发布后旧公钥保留至所有旧 Access Token 过期。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from structlog import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class JwtKeyPair:
    private_key: object | None
    public_key: object
    key_id: str


class JwtKeyManager:
    """JWT RS256 密钥管理器。"""

    def __init__(self) -> None:
        self._current: JwtKeyPair | None = None
        self._previous: JwtKeyPair | None = None
        self._load_keys()

    def _read_key(self, env_var: str, file_env_var: str) -> str:
        val = os.environ.get(env_var, "")
        if val:
            return val.replace("\\n", "\n")
        file_path = os.environ.get(file_env_var, "")
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                return f.read()
        return ""

    def _load_keys(self) -> None:
        priv_pem = self._read_key("EITP_JWT_PRIVATE_KEY", "EITP_JWT_PRIVATE_KEY_FILE")
        pub_pem = self._read_key("EITP_JWT_PUBLIC_KEY", "EITP_JWT_PUBLIC_KEY_FILE")
        key_id = os.environ.get("EITP_JWT_KEY_ID", "iam-key-v1")

        if not pub_pem:
            logger.warning("jwt_public_key_missing", msg="EITP_JWT_PUBLIC_KEY not set")
            return

        public_key = serialization.load_pem_public_key(pub_pem.encode())
        private_key: object | None = None
        if priv_pem:
            private_key = serialization.load_pem_private_key(priv_pem.encode(), password=None)

        self._current = JwtKeyPair(
            private_key=private_key,
            public_key=public_key,
            key_id=key_id,
        )

        prev_pub_pem = os.environ.get("EITP_JWT_PREVIOUS_PUBLIC_KEY", "")
        prev_key_id = os.environ.get("EITP_JWT_PREVIOUS_KEY_ID", "")
        if prev_pub_pem and prev_key_id:
            prev_public = serialization.load_pem_public_key(prev_pub_pem.encode())
            self._previous = JwtKeyPair(
                private_key=None,
                public_key=prev_public,
                key_id=prev_key_id,
            )

        logger.info("jwt_keys_loaded", current_kid=key_id, has_previous=self._previous is not None)

    @property
    def signing_key(self) -> JwtKeyPair:
        if self._current is None or self._current.private_key is None:
            raise RuntimeError("JWT signing key not available")
        return self._current

    def get_verification_key(self, key_id: str) -> object:
        if self._current and self._current.key_id == key_id:
            return self._current.public_key
        if self._previous and self._previous.key_id == key_id:
            return self._previous.public_key
        raise ValueError(f"Unknown key_id: {key_id}")

    @property
    def current_key_id(self) -> str:
        if self._current is None:
            raise RuntimeError("JWT keys not loaded")
        return self._current.key_id


_key_manager: JwtKeyManager | None = None


def get_key_manager() -> JwtKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = JwtKeyManager()
    return _key_manager
