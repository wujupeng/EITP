"""值对象基类 - 无唯一标识的不可变领域对象。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """值对象基类 - 通过属性值判断相等性，不可变。"""