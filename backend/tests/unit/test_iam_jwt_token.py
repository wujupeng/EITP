"""EITP-IAM-001 JWT Token 服务与 Refresh Token 轮换单元测试。"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.domain.authn.value_objects.tokens import AccessTokenClaims, TokenPair
from app.infrastructure.auth import jwt_key_manager as km_module
from app.infrastructure.auth.jwt_key_manager import JwtKeyManager
from app.infrastructure.auth.token_service import TokenService
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode

_KEY_ID = "test-key-001"


def _generate_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv_pem, pub_pem


@pytest.fixture
def token_service():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    old_env = {
        "EITP_JWT_PRIVATE_KEY": os.environ.get("EITP_JWT_PRIVATE_KEY"),
        "EITP_JWT_PUBLIC_KEY": os.environ.get("EITP_JWT_PUBLIC_KEY"),
        "EITP_JWT_KEY_ID": os.environ.get("EITP_JWT_KEY_ID"),
    }
    os.environ["EITP_JWT_PRIVATE_KEY"] = priv_pem
    os.environ["EITP_JWT_PUBLIC_KEY"] = pub_pem
    os.environ["EITP_JWT_KEY_ID"] = _KEY_ID
    km_module._key_manager = None

    yield TokenService()

    for k, v in old_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    km_module._key_manager = None


def _encode_token(token_service: TokenService, private_key_obj, kid: str, exp_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "jti": "jti-" + uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "is_platform_admin": False,
        "is_tenant_admin": False,
        "roles": [],
        "permissions": [],
    }
    return jwt.encode(payload, private_key_obj, algorithm="RS256", headers={"kid": kid})


class _InMemoryRefreshStore:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    async def save(self, token_hash: str, **info: object) -> None:
        self._store[token_hash] = {"is_revoked": False, **info}

    async def get(self, token_hash: str) -> dict | None:
        return self._store.get(token_hash)

    async def revoke(self, token_hash: str) -> None:
        if token_hash in self._store:
            self._store[token_hash]["is_revoked"] = True


class TokenServiceTest:
    def test_issue_and_verify_access_token(self, token_service: TokenService) -> None:
        uid = uuid4()
        tid = uuid4()
        token, claims = token_service.issue_access_token(
            user_id=uid,
            tenant_id=tid,
            roles=("admin",),
            permissions=("iam:user:read",),
            is_platform_admin=True,
        )
        assert isinstance(token, str)
        assert isinstance(claims, AccessTokenClaims)
        assert claims.sub == uid
        assert claims.tenant_id == tid
        verified = token_service.verify_access_token(token)
        assert verified.sub == uid
        assert verified.tenant_id == tid
        assert verified.is_platform_admin is True
        assert verified.roles == ("admin",)
        assert verified.permissions == ("iam:user:read",)

    def test_token_claims_completeness(self, token_service: TokenService) -> None:
        uid = uuid4()
        tid = uuid4()
        token, claims = token_service.issue_access_token(
            user_id=uid,
            tenant_id=tid,
            roles=("r1", "r2"),
            permissions=("p1", "p2"),
            is_platform_admin=False,
            is_tenant_admin=True,
        )
        assert isinstance(claims.sub, UUID)
        assert claims.sub == uid
        assert claims.tenant_id == tid
        assert isinstance(claims.jti, str) and len(claims.jti) > 0
        assert claims.iat < claims.exp
        assert claims.is_platform_admin is False
        assert claims.is_tenant_admin is True
        assert claims.roles == ("r1", "r2")
        assert claims.permissions == ("p1", "p2")
        header = jwt.get_unverified_header(token)
        assert header["kid"] == _KEY_ID
        assert header["alg"] == "RS256"

    def test_expired_token_rejected(self, token_service: TokenService) -> None:
        key_pair = token_service._km.signing_key
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "jti": "expired-jti",
            "iat": int((now - timedelta(minutes=60)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "is_platform_admin": False,
            "is_tenant_admin": False,
            "roles": [],
            "permissions": [],
        }
        token = jwt.encode(
            payload, key_pair.private_key, algorithm="RS256", headers={"kid": key_pair.key_id}
        )
        with pytest.raises(IAMError) as exc:
            token_service.verify_access_token(token)
        assert exc.value.code == IAMErrorCode.TOKEN_EXPIRED

    def test_invalid_signature_rejected(self, token_service: TokenService) -> None:
        other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pair = token_service._km.signing_key
        token = _encode_token(token_service, other_private, key_pair.key_id, timedelta(minutes=30))
        with pytest.raises(IAMError) as exc:
            token_service.verify_access_token(token)
        assert exc.value.code == IAMErrorCode.TOKEN_SIGNATURE_INVALID

    def test_unknown_kid_rejected(self, token_service: TokenService) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = _encode_token(token_service, private_key, "nonexistent-kid", timedelta(minutes=30))
        with pytest.raises(IAMError) as exc:
            token_service.verify_access_token(token)
        assert exc.value.code == IAMErrorCode.TOKEN_SIGNATURE_INVALID

    def test_generate_refresh_token(self, token_service: TokenService) -> None:
        raw, token_hash, expires_at = token_service.generate_refresh_token()
        assert isinstance(raw, str) and len(raw) > 0
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert token_hash == expected_hash
        assert expires_at > datetime.now(timezone.utc)

    def test_hash_refresh_token_deterministic(self, token_service: TokenService) -> None:
        raw = "some-refresh-token-value"
        h1 = token_service.hash_refresh_token(raw)
        h2 = token_service.hash_refresh_token(raw)
        assert h1 == h2
        assert h1 == hashlib.sha256(raw.encode()).hexdigest()

    def test_issue_token_pair(self, token_service: TokenService) -> None:
        uid = uuid4()
        tid = uuid4()
        pair = token_service.issue_token_pair(
            user_id=uid,
            tenant_id=tid,
            roles=("admin",),
            permissions=("iam:user:read",),
        )
        assert isinstance(pair, TokenPair)
        assert isinstance(pair.access_token, str)
        assert isinstance(pair.refresh_token, str)
        assert pair.access_token_expires_at < pair.refresh_token_expires_at
        verified = token_service.verify_access_token(pair.access_token)
        assert verified.sub == uid

    async def test_refresh_token_rotation_invalidates_old(self, token_service: TokenService) -> None:
        store = _InMemoryRefreshStore()
        old_raw, old_hash, _ = token_service.generate_refresh_token()
        await store.save(old_hash, user_id="u1")
        assert token_service.hash_refresh_token(old_raw) == old_hash

        new_raw, new_hash, _ = token_service.generate_refresh_token()
        await store.revoke(old_hash)
        await store.save(new_hash, user_id="u1")

        old_record = await store.get(old_hash)
        new_record = await store.get(new_hash)
        assert old_record is not None
        assert new_record is not None
        assert old_record["is_revoked"] is True
        assert new_record["is_revoked"] is False
        assert old_hash != new_hash
        assert old_raw != new_raw

    async def test_repeated_rotation_produces_distinct_tokens(self, token_service: TokenService) -> None:
        hashes: set[str] = set()
        raws: set[str] = set()
        for _ in range(5):
            raw, token_hash, _ = token_service.generate_refresh_token()
            hashes.add(token_hash)
            raws.add(raw)
        assert len(hashes) == 5
        assert len(raws) == 5


@pytest.fixture
def key_manager_factory():
    tracked = [
        "EITP_JWT_PRIVATE_KEY",
        "EITP_JWT_PUBLIC_KEY",
        "EITP_JWT_KEY_ID",
        "EITP_JWT_PREVIOUS_PUBLIC_KEY",
        "EITP_JWT_PREVIOUS_KEY_ID",
        "EITP_JWT_PRIVATE_KEY_FILE",
        "EITP_JWT_PUBLIC_KEY_FILE",
    ]
    old_env = {k: os.environ.get(k) for k in tracked}

    def _build(**env_vars: str | None) -> JwtKeyManager:
        for k in tracked:
            os.environ.pop(k, None)
        for k, v in env_vars.items():
            if v is not None:
                os.environ[k] = v
        km_module._key_manager = None
        return km_module.JwtKeyManager()

    yield _build

    for k, v in old_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    km_module._key_manager = None


class JwtKeyManagerTest:
    def test_current_key_id(self, key_manager_factory) -> None:
        priv, pub = _generate_key_pair()
        km = key_manager_factory(
            EITP_JWT_PRIVATE_KEY=priv, EITP_JWT_PUBLIC_KEY=pub, EITP_JWT_KEY_ID="kid-1"
        )
        assert km.current_key_id == "kid-1"
        assert km.signing_key.key_id == "kid-1"

    def test_signing_key_raises_when_no_private(self, key_manager_factory) -> None:
        _, pub = _generate_key_pair()
        km = key_manager_factory(EITP_JWT_PUBLIC_KEY=pub, EITP_JWT_KEY_ID="kid-1")
        with pytest.raises(RuntimeError):
            km.signing_key

    def test_current_key_id_raises_when_no_keys(self, key_manager_factory) -> None:
        km = key_manager_factory()
        with pytest.raises(RuntimeError):
            km.current_key_id

    def test_get_verification_key_current_and_previous(self, key_manager_factory) -> None:
        priv_cur, pub_cur = _generate_key_pair()
        _, pub_prev = _generate_key_pair()
        km = key_manager_factory(
            EITP_JWT_PRIVATE_KEY=priv_cur,
            EITP_JWT_PUBLIC_KEY=pub_cur,
            EITP_JWT_KEY_ID="cur",
            EITP_JWT_PREVIOUS_PUBLIC_KEY=pub_prev,
            EITP_JWT_PREVIOUS_KEY_ID="prev",
        )
        assert km.get_verification_key("cur") is not None
        assert km.get_verification_key("prev") is not None

    def test_get_verification_key_unknown_raises(self, key_manager_factory) -> None:
        priv, pub = _generate_key_pair()
        km = key_manager_factory(
            EITP_JWT_PRIVATE_KEY=priv, EITP_JWT_PUBLIC_KEY=pub, EITP_JWT_KEY_ID="kid-1"
        )
        with pytest.raises(ValueError):
            km.get_verification_key("unknown")

    def test_public_key_from_file(self, tmp_path, key_manager_factory) -> None:
        priv, pub = _generate_key_pair()
        key_file = tmp_path / "pub.pem"
        key_file.write_text(pub)
        km = key_manager_factory(
            EITP_JWT_PRIVATE_KEY=priv,
            EITP_JWT_PUBLIC_KEY_FILE=str(key_file),
            EITP_JWT_KEY_ID="file-kid",
        )
        assert km.current_key_id == "file-kid"
        assert km.signing_key.key_id == "file-kid"