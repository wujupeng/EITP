"""规格实例校验器 - SKU 创建/修改时校验规格实例符合引用的规格模板定义。

- 不符合模板定义拒绝创建（EITP_MDM_SPEC_INSTANCE_INVALID，spec 5.3.3.1）
- 校验规格模板循环引用（EITP_MDM_SPEC_TEMPLATE_CYCLE，spec 5.3.1.9）
"""

from __future__ import annotations

from uuid import UUID

from app.domain.group_catalog.aggregates.spec_template_aggregate import (
    SpecificationTemplateAggregate,
)


class SpecificationInstanceValidator:
    """规格实例校验器。"""

    @staticmethod
    def validate(
        template: SpecificationTemplateAggregate,
        instance: dict,
    ) -> bool:
        """校验规格实例符合模板定义。"""
        return template.validate_instance(instance)

    @staticmethod
    def validate_no_template_cycle(
        template_id: UUID,
        dependency_map: dict[UUID, list[UUID]],
        visited: set[UUID] | None = None,
        path: list[UUID] | None = None,
    ) -> None:
        """校验规格模板引用无循环引用（spec 5.3.1.9）。

        Args:
            template_id: 当前模板 ID
            dependency_map: 模板依赖关系 {template_id: [dep_template_id, ...]}
        """
        from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode

        if visited is None:
            visited = set()
        if path is None:
            path = []

        if template_id in path:
            cycle = path[path.index(template_id):] + [template_id]
            raise MDMError(
                MDMErrorCode.SPEC_TEMPLATE_CYCLE,
                f"规格模板检测到循环引用: {' -> '.join(str(t) for t in cycle)}",
            )

        if template_id in visited:
            return

        visited.add(template_id)
        path.append(template_id)

        for dep_id in dependency_map.get(template_id, []):
            SpecificationInstanceValidator.validate_no_template_cycle(
                dep_id, dependency_map, visited, path
            )

        path.pop()