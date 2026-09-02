"""CoSigner 单元测试 - 防代签（同人拒绝）+ 角色校验 + 默认角色。

覆盖 application/rel/co_signer.py 的 verify() 防代签（releaser==security_officer 拒绝）、
role_checker 注入校验发布经理/安全负责人角色、无 role_checker 时跳过角色校验、
自定义角色名、错误码映射。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.application.rel.co_signer import CoSigner
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


class CoSignerTest:
    """CoSigner 联合签发器防代签与角色校验测试。"""

    # --- 防代签 ---

    async def test_same_person_rejected_anti_proxy_signing(self) -> None:
        signer = CoSigner()
        with pytest.raises(RELError) as exc:
            await signer.verify("alice", "alice")
        assert exc.value.code == RELErrorCode.CO_SIGN_ALREADY_SIGNED
        assert "anti-proxy-signing" in exc.value.message

    async def test_different_persons_pass_without_role_checker(self) -> None:
        signer = CoSigner()
        await signer.verify("alice", "bob")

    # --- 无 role_checker 跳过角色校验 ---

    async def test_no_role_checker_skips_role_validation(self) -> None:
        signer = CoSigner(role_checker=None)
        await signer.verify("any_user", "any_other_user")

    # --- role_checker 角色校验通过 ---

    async def test_both_roles_present_passes(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(
            side_effect=lambda u: (
                ["RELEASE_MANAGER"] if u == "alice" else ["SECURITY_OFFICER"]
            )
        )
        signer = CoSigner(role_checker=role_checker)
        await signer.verify("alice", "bob")
        role_checker.get_user_roles.assert_any_call("alice")
        role_checker.get_user_roles.assert_any_call("bob")

    # --- role_checker 角色校验失败 ---

    async def test_releaser_missing_role_raises(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(return_value=["VIEWER"])
        signer = CoSigner(role_checker=role_checker)
        with pytest.raises(RELError) as exc:
            await signer.verify("alice", "bob")
        assert exc.value.code == RELErrorCode.CO_SIGN_UNAUTHORIZED_RELEASER

    async def test_security_officer_missing_role_raises(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(
            side_effect=lambda u: (
                ["RELEASE_MANAGER"] if u == "alice" else ["VIEWER"]
            )
        )
        signer = CoSigner(role_checker=role_checker)
        with pytest.raises(RELError) as exc:
            await signer.verify("alice", "bob")
        assert exc.value.code == RELErrorCode.CO_SIGN_UNAUTHORIZED_SECURITY

    async def test_same_person_checked_before_roles(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(return_value=["RELEASE_MANAGER"])
        signer = CoSigner(role_checker=role_checker)
        with pytest.raises(RELError) as exc:
            await signer.verify("alice", "alice")
        assert exc.value.code == RELErrorCode.CO_SIGN_ALREADY_SIGNED
        role_checker.get_user_roles.assert_not_called()

    # --- 自定义角色名 ---

    async def test_custom_role_names(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(
            side_effect=lambda u: (
                ["CUSTOM_RELEASE"] if u == "a" else ["CUSTOM_SEC"]
            )
        )
        signer = CoSigner(
            releaser_role="CUSTOM_RELEASE",
            security_role="CUSTOM_SEC",
            role_checker=role_checker,
        )
        await signer.verify("a", "b")

    async def test_custom_role_names_mismatch_raises(self) -> None:
        role_checker = AsyncMock()
        role_checker.get_user_roles = AsyncMock(return_value=["RELEASE_MANAGER"])
        signer = CoSigner(
            releaser_role="CUSTOM_RELEASE",
            role_checker=role_checker,
        )
        with pytest.raises(RELError) as exc:
            await signer.verify("a", "b")
        assert exc.value.code == RELErrorCode.CO_SIGN_UNAUTHORIZED_RELEASER