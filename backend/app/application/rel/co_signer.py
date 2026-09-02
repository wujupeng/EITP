"""联合签发器 - CoSigner。"""

from __future__ import annotations

from structlog import get_logger

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError

logger = get_logger(__name__)


class CoSigner:
    """联合签发器 - 发布经理 + 安全负责人双方凭证校验 + 防代签。"""

    def __init__(
        self,
        releaser_role: str = "RELEASE_MANAGER",
        security_role: str = "SECURITY_OFFICER",
        role_checker: object | None = None,
    ) -> None:
        self._releaser_role = releaser_role
        self._security_role = security_role
        self._role_checker = role_checker

    async def verify(
        self,
        releaser: str,
        security_officer: str,
    ) -> None:
        if releaser == security_officer:
            raise RELError(
                RELErrorCode.CO_SIGN_ALREADY_SIGNED,
                "releaser and security_officer must be different persons (anti-proxy-signing)",
            )

        if self._role_checker is not None:
            releaser_roles = await self._role_checker.get_user_roles(releaser)
            if self._releaser_role not in releaser_roles:
                raise RELError(
                    RELErrorCode.CO_SIGN_UNAUTHORIZED_RELEASER,
                    f"user {releaser} does not have role {self._releaser_role}",
                )

            security_roles = await self._role_checker.get_user_roles(security_officer)
            if self._security_role not in security_roles:
                raise RELError(
                    RELErrorCode.CO_SIGN_UNAUTHORIZED_SECURITY,
                    f"user {security_officer} does not have role {self._security_role}",
                )

        logger.info(
            "co_sign_verified",
            releaser=releaser,
            security_officer=security_officer,
        )