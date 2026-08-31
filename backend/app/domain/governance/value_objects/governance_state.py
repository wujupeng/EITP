"""治理状态枚举与状态流转校验。

状态机：DRAFT → SUBMITTED → APPROVED → PUBLISHED
                         ↘ REJECTED
                               PUBLISHED → ROLLED_BACK

禁止非法状态跳转（spec 5.6.1.11）。
"""

from __future__ import annotations

from enum import Enum

from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class GovernanceState(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ROLLED_BACK = "rolled_back"


VALID_TRANSITIONS: dict[GovernanceState, set[GovernanceState]] = {
    GovernanceState.DRAFT: {GovernanceState.SUBMITTED},
    GovernanceState.SUBMITTED: {GovernanceState.APPROVED, GovernanceState.REJECTED},
    GovernanceState.APPROVED: {GovernanceState.PUBLISHED},
    GovernanceState.REJECTED: set(),
    GovernanceState.PUBLISHED: {GovernanceState.ROLLED_BACK},
    GovernanceState.ROLLED_BACK: set(),
}


def validate_state_transition(from_state: GovernanceState, to_state: GovernanceState) -> None:
    """校验状态流转合法性，非法跳转被拒绝（spec 5.6.1.11）。"""
    if to_state not in VALID_TRANSITIONS.get(from_state, set()):
        raise MDMError(
            MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION,
            f"非法治理状态跳转: {from_state.value} → {to_state.value}",
        )


def is_editable(state: GovernanceState) -> bool:
    """已提交变更申请不可修改内容（spec 5.6.1.3）。"""
    return state == GovernanceState.DRAFT