"""密码强度校验器 - 独立于策略聚合根的校验服务。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    is_valid: bool
    violations: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid


class PasswordStrengthValidator:
    """密码强度校验器。

    校验规则：
    - 最小长度 12
    - 包含大写/小写/数字/特殊字符四类中至少三类
    - 不得包含用户名与邮箱子串
    """

    def validate(
        self,
        password: str,
        min_length: int = 12,
        required_categories: int = 3,
        username: str = "",
        email: str = "",
    ) -> ValidationResult:
        violations: list[str] = []

        if len(password) < min_length:
            violations.append(f"密码长度不足，最少需要 {min_length} 位")

        categories = 0
        if any(c.islower() for c in password):
            categories += 1
        if any(c.isupper() for c in password):
            categories += 1
        if any(c.isdigit() for c in password):
            categories += 1
        if any(not c.isalnum() for c in password):
            categories += 1

        if categories < required_categories:
            violations.append(
                f"密码字符类别不足（{categories}/{required_categories}），需包含大写/小写/数字/特殊字符中至少 {required_categories} 类"
            )

        if username and len(username) >= 3 and username.lower() in password.lower():
            violations.append("密码不得包含用户名")

        if email:
            email_prefix = email.split("@")[0]
            if len(email_prefix) >= 3 and email_prefix.lower() in password.lower():
                violations.append("密码不得包含邮箱前缀")

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
        )