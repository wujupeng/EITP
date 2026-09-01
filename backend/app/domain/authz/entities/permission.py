"""权限实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Permission:
    """权限实体 - 全局共享，不按租户隔离。"""

    id: UUID = field(default_factory=uuid4)
    code: str = ""
    name: str = ""
    module: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, code: str, name: str, module: str, description: str = "") -> Permission:
        return cls(code=code, name=name, module=module, description=description)


BUILTIN_PERMISSIONS: list[dict[str, str]] = [
    {"code": "iam:user:read", "name": "查看用户", "module": "iam"},
    {"code": "iam:user:write", "name": "管理用户", "module": "iam"},
    {"code": "iam:role:read", "name": "查看角色", "module": "iam"},
    {"code": "iam:role:write", "name": "管理角色", "module": "iam"},
    {"code": "iam:audit:read", "name": "查看审计", "module": "iam"},
    {"code": "iam:datascope:write", "name": "管理数据权限", "module": "iam"},
    {"code": "tenant:hierarchy:read", "name": "查看层级", "module": "tenant"},
    {"code": "tenant:hierarchy:write", "name": "管理层级", "module": "tenant"},
    {"code": "tenant:config:read", "name": "查看配置", "module": "tenant"},
    {"code": "tenant:config:write", "name": "管理配置", "module": "tenant"},
    {"code": "platform:tenant:read", "name": "查看租户", "module": "platform"},
    {"code": "platform:tenant:write", "name": "管理租户", "module": "platform"},
]


MDM_PERMISSIONS: list[dict[str, str]] = [
    {"code": "mdm:group_product:manage", "name": "管理集团商品", "module": "mdm", "description": "集团级 - 创建/编辑/发布集团商品"},
    {"code": "mdm:group_product:approve", "name": "审批集团商品", "module": "mdm", "description": "集团级 - 审批集团商品发布"},
    {"code": "mdm:group_sku:manage", "name": "管理集团SKU", "module": "mdm", "description": "集团级 - 管理集团SKU"},
    {"code": "mdm:group_category:manage", "name": "管理集团分类", "module": "mdm", "description": "集团级 - 管理集团分类树"},
    {"code": "mdm:group_brand:manage", "name": "管理集团品牌", "module": "mdm", "description": "集团级 - 管理集团品牌"},
    {"code": "mdm:group_unit:manage", "name": "管理集团单位", "module": "mdm", "description": "集团级 - 管理集团单位与换算"},
    {"code": "mdm:spec_template:manage", "name": "管理规格模板", "module": "mdm", "description": "集团级 - 管理规格模板"},
    {"code": "mdm:attribute_template:manage", "name": "管理属性模板", "module": "mdm", "description": "集团级 - 管理属性模板"},
    {"code": "mdm:enterprise_product:manage", "name": "管理企业商品", "module": "mdm", "description": "企业级 - 管理企业商品引用"},
    {"code": "mdm:enterprise_product:approve", "name": "审批企业商品", "module": "mdm", "description": "企业级 - 审批企业商品定制"},
    {"code": "mdm:enterprise_customization:manage", "name": "管理企业定制", "module": "mdm", "description": "企业级 - 管理商品差异化定制"},
    {"code": "mdm:product_reference:create", "name": "创建商品引用", "module": "mdm", "description": "企业级 - 引用集团商品"},
    {"code": "mdm:product_reference:release", "name": "释放商品引用", "module": "mdm", "description": "企业级 - 释放集团商品引用"},
    {"code": "mdm:governance:submit", "name": "提交治理申请", "module": "mdm", "description": "提交主数据变更治理申请"},
    {"code": "mdm:governance:approve", "name": "审批治理申请", "module": "mdm", "description": "审批主数据变更治理申请"},
    {"code": "mdm:governance:publish", "name": "发布治理结果", "module": "mdm", "description": "发布治理审批通过的主数据"},
    {"code": "mdm:governance:rollback", "name": "回滚治理版本", "module": "mdm", "description": "回滚主数据到历史版本"},
    {"code": "mdm:governance:query", "name": "查询治理工作流", "module": "mdm", "description": "查询治理申请与审批记录"},
    {"code": "mdm:version:compare", "name": "版本对比", "module": "mdm", "description": "对比主数据版本差异"},
    {"code": "mdm:version:query", "name": "版本查询", "module": "mdm", "description": "查询主数据版本历史"},
    {"code": "mdm:negative_policy:config", "name": "配置负库存策略", "module": "mdm", "description": "企业级 - 配置负库存策略"},
    {"code": "mdm:negative_policy:audit:query", "name": "查询负库存策略审计", "module": "mdm", "description": "查询负库存策略变更审计"},
    {"code": "mdm:master_data:query", "name": "查询主数据", "module": "mdm", "description": "查询主数据中心数据"},
]


GROUP_LEVEL_MDM_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in MDM_PERMISSIONS if p["description"].startswith("集团级")
)


ENTERPRISE_LEVEL_MDM_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in MDM_PERMISSIONS if p["description"].startswith("企业级")
)


MDM_MENU_TREE: dict = {
    "group_level": [
        {
            "key": "mdm-group-product",
            "label": "集团商品目录",
            "permission": "mdm:group_product:manage",
            "feature_flag": "mdm_group_catalog",
            "children": [
                {"key": "mdm-group-product-list", "label": "商品列表", "permission": "mdm:group_product:manage"},
                {"key": "mdm-group-sku", "label": "SKU管理", "permission": "mdm:group_sku:manage"},
            ],
        },
        {
            "key": "mdm-group-category",
            "label": "集团分类树",
            "permission": "mdm:group_category:manage",
            "feature_flag": "mdm_group_catalog",
        },
        {
            "key": "mdm-group-brand",
            "label": "集团品牌",
            "permission": "mdm:group_brand:manage",
            "feature_flag": "mdm_group_catalog",
        },
        {
            "key": "mdm-group-unit",
            "label": "集团计量单位",
            "permission": "mdm:group_unit:manage",
            "feature_flag": "mdm_group_catalog",
        },
        {
            "key": "mdm-spec-template",
            "label": "规格模板",
            "permission": "mdm:spec_template:manage",
            "feature_flag": "mdm_group_catalog",
        },
        {
            "key": "mdm-attribute-template",
            "label": "属性模板",
            "permission": "mdm:attribute_template:manage",
            "feature_flag": "mdm_group_catalog",
        },
    ],
    "tenant_level": [
        {
            "key": "mdm-enterprise-product",
            "label": "企业商品",
            "permission": "mdm:enterprise_product:manage",
            "feature_flag": "mdm_enterprise_product",
            "children": [
                {"key": "mdm-enterprise-product-list", "label": "商品列表", "permission": "mdm:enterprise_product:manage"},
                {"key": "mdm-product-reference", "label": "商品引用", "permission": "mdm:product_reference:create"},
                {"key": "mdm-enterprise-customization", "label": "企业定制", "permission": "mdm:enterprise_customization:manage"},
            ],
        },
        {
            "key": "mdm-governance",
            "label": "治理工作流",
            "permission": "mdm:governance:query",
            "feature_flag": "mdm_governance",
        },
        {
            "key": "mdm-version-management",
            "label": "版本管理",
            "permission": "mdm:version:query",
            "feature_flag": "mdm_governance",
        },
        {
            "key": "mdm-negative-policy",
            "label": "负库存策略",
            "permission": "mdm:negative_policy:config",
            "feature_flag": "mdm_negative_policy",
        },
        {
            "key": "mdm-master-data-audit",
            "label": "主数据审计",
            "permission": "mdm:master_data:query",
            "feature_flag": "mdm_group_catalog",
        },
    ],
}


WMS_PERMISSIONS: list[dict[str, str]] = [
    {"code": "wms:space:manage", "name": "仓储空间管理", "module": "wms", "description": "企业级 - 管理仓库/库区/区域/库位"},
    {"code": "wms:space:query", "name": "查询仓储空间", "module": "wms", "description": "企业级 - 查询仓库空间层级"},
    {"code": "wms:position:query", "name": "查询库存位置", "module": "wms", "description": "企业级 - 查询库存物理分布"},
    {"code": "wms:task:manage", "name": "管理WMS任务", "module": "wms", "description": "企业级 - 创建/编辑WMS作业任务"},
    {"code": "wms:task:assign", "name": "分配WMS任务", "module": "wms", "description": "企业级 - 分配作业任务给执行人"},
    {"code": "wms:task:claim", "name": "认领WMS任务", "module": "wms", "description": "企业级 - 执行人认领作业任务"},
    {"code": "wms:task:cancel", "name": "取消WMS任务", "module": "wms", "description": "企业级 - 取消作业任务"},
    {"code": "wms:task:query", "name": "查询WMS任务", "module": "wms", "description": "企业级 - 查询作业任务列表与详情"},
    {"code": "wms:receiving:execute", "name": "执行收货作业", "module": "wms", "description": "企业级 - 执行收货作业"},
    {"code": "wms:receiving:query", "name": "查询收货作业", "module": "wms", "description": "企业级 - 查询收货作业记录"},
    {"code": "wms:putaway:execute", "name": "执行上架作业", "module": "wms", "description": "企业级 - 执行上架作业"},
    {"code": "wms:putaway:query", "name": "查询上架作业", "module": "wms", "description": "企业级 - 查询上架作业记录"},
    {"code": "wms:picking:execute", "name": "执行拣货作业", "module": "wms", "description": "企业级 - 执行拣货作业"},
    {"code": "wms:picking:query", "name": "查询拣货作业", "module": "wms", "description": "企业级 - 查询拣货作业记录"},
    {"code": "wms:transfer:execute", "name": "执行移库作业", "module": "wms", "description": "企业级 - 执行移库作业"},
    {"code": "wms:transfer:approve", "name": "审批移库作业", "module": "wms", "description": "企业级 - 审批跨仓移库申请"},
    {"code": "wms:transfer:query", "name": "查询移库作业", "module": "wms", "description": "企业级 - 查询移库作业记录"},
    {"code": "wms:shipping:execute", "name": "执行发货作业", "module": "wms", "description": "企业级 - 执行发货作业"},
    {"code": "wms:shipping:query", "name": "查询发货作业", "module": "wms", "description": "企业级 - 查询发货作业记录"},
    {"code": "wms:reconcile:execute", "name": "执行对账", "module": "wms", "description": "企业级 - 执行WMS与INV库存对账"},
]


ENTERPRISE_LEVEL_WMS_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in WMS_PERMISSIONS if p["description"].startswith("企业级")
)


WMS_MENU_TREE: dict = {
    "tenant_level": [
        {
            "key": "wms-space",
            "label": "仓储空间管理",
            "permission": "wms:space:manage",
            "feature_flag": "wms_space",
            "children": [
                {"key": "wms-warehouse", "label": "仓库管理", "permission": "wms:space:manage"},
                {"key": "wms-zone", "label": "库区管理", "permission": "wms:space:manage"},
                {"key": "wms-location", "label": "库位管理", "permission": "wms:space:manage"},
            ],
        },
        {
            "key": "wms-position",
            "label": "库存位置查询",
            "permission": "wms:position:query",
            "feature_flag": "wms_space",
        },
        {
            "key": "wms-receiving",
            "label": "收货作业台",
            "permission": "wms:receiving:execute",
            "feature_flag": "wms_receiving",
        },
        {
            "key": "wms-putaway",
            "label": "上架作业台",
            "permission": "wms:putaway:execute",
            "feature_flag": "wms_putaway",
        },
        {
            "key": "wms-picking",
            "label": "拣货作业台",
            "permission": "wms:picking:execute",
            "feature_flag": "wms_picking",
        },
        {
            "key": "wms-transfer",
            "label": "移库作业台",
            "permission": "wms:transfer:execute",
            "feature_flag": "wms_transfer",
        },
        {
            "key": "wms-shipping",
            "label": "发货作业台",
            "permission": "wms:shipping:execute",
            "feature_flag": "wms_shipping",
        },
        {
            "key": "wms-task",
            "label": "WMS任务管理",
            "permission": "wms:task:manage",
            "feature_flag": "wms_task",
        },
        {
            "key": "wms-reconcile",
            "label": "对账管理",
            "permission": "wms:reconcile:execute",
            "feature_flag": "wms_reconcile",
        },
    ],
}


PUR_PERMISSIONS: list[dict[str, str]] = [
    {"code": "pur:supplier:manage", "name": "供应商管理", "module": "pur", "description": "企业级 - 管理供应商档案/供货范围"},
    {"code": "pur:supplier:query", "name": "查询供应商", "module": "pur", "description": "企业级 - 查询供应商列表与详情"},
    {"code": "pur:quotation:manage", "name": "报价单管理", "module": "pur", "description": "企业级 - 管理供应商报价单"},
    {"code": "pur:evaluation:manage", "name": "供应商评估", "module": "pur", "description": "企业级 - 供应商绩效评估"},
    {"code": "pur:request:create", "name": "创建采购申请", "module": "pur", "description": "企业级 - 发起采购申请"},
    {"code": "pur:request:approve", "name": "审批采购申请", "module": "pur", "description": "企业级 - 审批采购申请"},
    {"code": "pur:request:query", "name": "查询采购申请", "module": "pur", "description": "企业级 - 查询采购申请列表"},
    {"code": "pur:order:create", "name": "创建采购订单", "module": "pur", "description": "企业级 - 创建采购订单"},
    {"code": "pur:order:approve", "name": "审批采购订单", "module": "pur", "description": "企业级 - 审批采购订单"},
    {"code": "pur:order:send", "name": "发送采购订单", "module": "pur", "description": "企业级 - 发送采购订单给供应商"},
    {"code": "pur:order:change", "name": "变更采购订单", "module": "pur", "description": "企业级 - 变更已审批采购订单"},
    {"code": "pur:order:cancel", "name": "取消采购订单", "module": "pur", "description": "企业级 - 取消采购订单"},
    {"code": "pur:order:close", "name": "关闭采购订单", "module": "pur", "description": "企业级 - 关闭已完成的采购订单"},
    {"code": "pur:order:query", "name": "查询采购订单", "module": "pur", "description": "企业级 - 查询采购订单列表与详情"},
    {"code": "pur:asn:manage", "name": "管理到货通知", "module": "pur", "description": "企业级 - 创建/管理ASN到货通知"},
    {"code": "pur:receipt:execute", "name": "执行采购收货", "module": "pur", "description": "企业级 - 确认采购到货收货"},
    {"code": "pur:receipt:query", "name": "查询采购收货", "module": "pur", "description": "企业级 - 查询采购收货记录"},
    {"code": "pur:return:create", "name": "创建采购退货", "module": "pur", "description": "企业级 - 发起采购退货申请"},
    {"code": "pur:return:approve", "name": "审批采购退货", "module": "pur", "description": "企业级 - 审批采购退货申请"},
    {"code": "pur:return:query", "name": "查询采购退货", "module": "pur", "description": "企业级 - 查询采购退货记录"},
    {"code": "pur:settlement:execute", "name": "执行采购结算", "module": "pur", "description": "企业级 - 执行采购对账与结算"},
    {"code": "pur:invoice:manage", "name": "发票管理", "module": "pur", "description": "企业级 - 管理采购发票与匹配"},
    {"code": "pur:payment:request", "name": "付款申请", "module": "pur", "description": "企业级 - 发起付款申请"},
    {"code": "pur:payment:confirm", "name": "付款确认", "module": "pur", "description": "企业级 - 确认付款完成"},
    {"code": "pur:reconcile:execute", "name": "采购对账", "module": "pur", "description": "企业级 - 执行采购WMS INV三边对账"},
]


ENTERPRISE_LEVEL_PUR_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in PUR_PERMISSIONS if p["description"].startswith("企业级")
)


PUR_MENU_TREE: dict = {
    "tenant_level": [
        {
            "key": "pur-supplier",
            "label": "供应商管理",
            "permission": "pur:supplier:manage",
            "feature_flag": "pur_supplier",
            "children": [
                {"key": "pur-supplier-list", "label": "供应商档案", "permission": "pur:supplier:manage"},
                {"key": "pur-quotation", "label": "报价单管理", "permission": "pur:quotation:manage"},
                {"key": "pur-evaluation", "label": "供应商评估", "permission": "pur:evaluation:manage"},
            ],
        },
        {
            "key": "pur-request",
            "label": "采购申请",
            "permission": "pur:request:create",
            "feature_flag": "pur_request",
        },
        {
            "key": "pur-order",
            "label": "采购订单",
            "permission": "pur:order:create",
            "feature_flag": "pur_order",
        },
        {
            "key": "pur-receipt",
            "label": "采购到货",
            "permission": "pur:receipt:execute",
            "feature_flag": "pur_receipt",
        },
        {
            "key": "pur-return",
            "label": "采购退货",
            "permission": "pur:return:create",
            "feature_flag": "pur_return",
        },
        {
            "key": "pur-settlement",
            "label": "采购结算",
            "permission": "pur:settlement:execute",
            "feature_flag": "pur_settlement",
            "children": [
                {"key": "pur-invoice", "label": "发票管理", "permission": "pur:invoice:manage"},
                {"key": "pur-payment", "label": "付款申请", "permission": "pur:payment:request"},
            ],
        },
        {
            "key": "pur-reconcile",
            "label": "采购对账",
            "permission": "pur:reconcile:execute",
            "feature_flag": "pur_reconcile",
        },
    ],
}


SAL_PERMISSIONS: list[dict[str, str]] = [
    {"code": "sal:customer:manage", "name": "客户管理", "module": "sal", "description": "企业级 - 管理客户档案/地址/联系人"},
    {"code": "sal:customer:query", "name": "查询客户", "module": "sal", "description": "企业级 - 查询客户列表与详情"},
    {"code": "sal:category:manage", "name": "客户分类管理", "module": "sal", "description": "企业级 - 管理客户分类"},
    {"code": "sal:credit:manage", "name": "信用额度管理", "module": "sal", "description": "企业级 - 管理客户信用额度"},
    {"code": "sal:pricing:manage", "name": "价格体系管理", "module": "sal", "description": "企业级 - 管理客户价格体系"},
    {"code": "sal:quotation:create", "name": "创建销售报价", "module": "sal", "description": "企业级 - 创建销售报价单"},
    {"code": "sal:quotation:approve", "name": "审批销售报价", "module": "sal", "description": "企业级 - 审批销售报价单"},
    {"code": "sal:quotation:convert", "name": "报价转订单", "module": "sal", "description": "企业级 - 报价单转销售订单"},
    {"code": "sal:quotation:query", "name": "查询销售报价", "module": "sal", "description": "企业级 - 查询销售报价单"},
    {"code": "sal:order:create", "name": "创建销售订单", "module": "sal", "description": "企业级 - 创建销售订单"},
    {"code": "sal:order:approve", "name": "审批销售订单", "module": "sal", "description": "企业级 - 审批销售订单"},
    {"code": "sal:order:confirm", "name": "确认销售订单", "module": "sal", "description": "企业级 - 确认销售订单(触发预留)"},
    {"code": "sal:order:change", "name": "变更销售订单", "module": "sal", "description": "企业级 - 变更已审批销售订单"},
    {"code": "sal:order:cancel", "name": "取消销售订单", "module": "sal", "description": "企业级 - 取消销售订单"},
    {"code": "sal:order:close", "name": "关闭销售订单", "module": "sal", "description": "企业级 - 关闭已完成的销售订单"},
    {"code": "sal:order:query", "name": "查询销售订单", "module": "sal", "description": "企业级 - 查询销售订单列表与详情"},
    {"code": "sal:shipment:create", "name": "创建发货单", "module": "sal", "description": "企业级 - 创建发货单(部分发货)"},
    {"code": "sal:shipment:confirm", "name": "确认发货", "module": "sal", "description": "企业级 - 确认发货(触发WMS Shipping)"},
    {"code": "sal:shipment:query", "name": "查询发货", "module": "sal", "description": "企业级 - 查询发货记录"},
    {"code": "sal:packing:manage", "name": "包装管理", "module": "sal", "description": "企业级 - 管理包装作业"},
    {"code": "sal:return:create", "name": "创建销售退货", "module": "sal", "description": "企业级 - 发起销售退货申请"},
    {"code": "sal:return:approve", "name": "审批销售退货", "module": "sal", "description": "企业级 - 审批销售退货申请"},
    {"code": "sal:return:execute", "name": "执行销售退货", "module": "sal", "description": "企业级 - 执行退货收货与入库"},
    {"code": "sal:return:query", "name": "查询销售退货", "module": "sal", "description": "企业级 - 查询销售退货记录"},
    {"code": "sal:settlement:execute", "name": "执行销售结算", "module": "sal", "description": "企业级 - 执行销售对账与结算"},
    {"code": "sal:invoice:create", "name": "开具销售发票", "module": "sal", "description": "企业级 - 开具销售发票"},
    {"code": "sal:payment:request", "name": "收款申请", "module": "sal", "description": "企业级 - 发起收款申请"},
    {"code": "sal:payment:confirm", "name": "收款确认", "module": "sal", "description": "企业级 - 确认收款完成"},
    {"code": "sal:reconcile:execute", "name": "销售对账", "module": "sal", "description": "企业级 - 执行销售WMS INV三边对账"},
]


ENTERPRISE_LEVEL_SAL_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in SAL_PERMISSIONS if p["description"].startswith("企业级")
)


SAL_MENU_TREE: dict = {
    "tenant_level": [
        {
            "key": "sal-customer",
            "label": "客户管理",
            "permission": "sal:customer:manage",
            "feature_flag": "sal_customer",
            "children": [
                {"key": "sal-customer-list", "label": "客户档案", "permission": "sal:customer:manage"},
                {"key": "sal-category", "label": "客户分类", "permission": "sal:category:manage"},
                {"key": "sal-credit", "label": "信用额度", "permission": "sal:credit:manage"},
                {"key": "sal-pricing", "label": "价格体系", "permission": "sal:pricing:manage"},
            ],
        },
        {
            "key": "sal-quotation",
            "label": "销售报价",
            "permission": "sal:quotation:create",
            "feature_flag": "sal_quotation",
        },
        {
            "key": "sal-order",
            "label": "销售订单",
            "permission": "sal:order:create",
            "feature_flag": "sal_order",
        },
        {
            "key": "sal-shipment",
            "label": "发货管理",
            "permission": "sal:shipment:create",
            "feature_flag": "sal_shipment",
            "children": [
                {"key": "sal-packing", "label": "包装管理", "permission": "sal:packing:manage"},
            ],
        },
        {
            "key": "sal-return",
            "label": "销售退货",
            "permission": "sal:return:create",
            "feature_flag": "sal_return",
        },
        {
            "key": "sal-settlement",
            "label": "销售结算",
            "permission": "sal:settlement:execute",
            "feature_flag": "sal_settlement",
            "children": [
                {"key": "sal-invoice", "label": "发票管理", "permission": "sal:invoice:create"},
                {"key": "sal-payment", "label": "收款管理", "permission": "sal:payment:request"},
            ],
        },
        {
            "key": "sal-reconcile",
            "label": "销售对账",
            "permission": "sal:reconcile:execute",
            "feature_flag": "sal_reconcile",
        },
    ],
}


SEC_PERMISSIONS: list[dict[str, str]] = [
    {"code": "sec:cert:execute", "name": "执行认证", "module": "sec", "description": "平台级 - 执行多租户隔离认证矩阵"},
    {"code": "sec:cert:issue", "name": "颁发证书", "module": "sec", "description": "平台级 - 颁发 Multi-Tenant Isolation Certification"},
    {"code": "sec:cert:revoke", "name": "撤销证书", "module": "sec", "description": "平台级 - 撤销已颁发的认证证书"},
    {"code": "sec:cert:verify", "name": "验证证书", "module": "sec", "description": "平台级 - 验证认证证书签名与有效性"},
    {"code": "sec:report:view", "name": "查看认证报告", "module": "sec", "description": "平台级 - 查看认证报告与证据"},
    {"code": "sec:report:export", "name": "导出认证报告", "module": "sec", "description": "平台级 - 导出认证报告 JSON/HTML/PDF"},
    {"code": "sec:report:evidence:view", "name": "查看证据", "module": "sec", "description": "平台级 - 下钻查看认证项证据快照"},
    {"code": "sec:config:manage", "name": "管理认证配置", "module": "sec", "description": "平台级 - 配置认证矩阵层级与阈值"},
    {"code": "sec:config:item:skip", "name": "跳过认证项", "module": "sec", "description": "平台级 - 跳过特定认证项（需显式原因）"},
    {"code": "sec:audit:view", "name": "查看认证审计", "module": "sec", "description": "平台级 - 查看认证审计日志"},
    {"code": "sec:audit:export", "name": "导出认证审计", "module": "sec", "description": "平台级 - 导出认证审计日志"},
    {"code": "sec:platform:access:request", "name": "申请平台访问", "module": "sec", "description": "平台级 - 申请平台管理员业务数据访问"},
    {"code": "sec:platform:access:approve", "name": "审批平台访问", "module": "sec", "description": "平台级 - 审批平台管理员业务数据访问申请"},
    {"code": "sec:redis:scan", "name": "Redis Key 扫描", "module": "sec", "description": "平台级 - 扫描 Redis Key 租户前缀合规性"},
    {"code": "sec:join:test", "name": "JOIN 泄露测试", "module": "sec", "description": "平台级 - 执行 JOIN 跨租户泄露测试"},
    {"code": "sec:attack:chain", "name": "攻击链 E2E", "module": "sec", "description": "平台级 - 执行 14 步完整攻击链 E2E 验证"},
    {"code": "sec:matrix:execute", "name": "执行认证矩阵", "module": "sec", "description": "平台级 - 执行 15 层 × 7 模块 × 9 操作全矩阵"},
    {"code": "sec:evidence:capture", "name": "采集证据", "module": "sec", "description": "平台级 - 采集认证项证据快照"},
    {"code": "sec:certificate:sign", "name": "签署证书", "module": "sec", "description": "平台级 - HMAC-SHA256 签署认证证书"},
    {"code": "sec:tenant:isolate", "name": "租户隔离验证", "module": "sec", "description": "平台级 - 验证租户数据隔离完整性"},
]


ENTERPRISE_LEVEL_SEC_PERMISSIONS: frozenset[str] = frozenset(
    p["code"] for p in SEC_PERMISSIONS if p["description"].startswith("企业级")
)


SEC_MENU_TREE: dict = {
    "platform_level": [
        {
            "key": "sec-cert",
            "label": "安全认证",
            "permission": "sec:cert:execute",
            "feature_flag": "sec_certification",
            "children": [
                {"key": "sec-cert-execute", "label": "认证执行", "permission": "sec:cert:execute"},
                {"key": "sec-cert-matrix", "label": "认证矩阵", "permission": "sec:matrix:execute"},
                {"key": "sec-cert-attack-chain", "label": "攻击链 E2E", "permission": "sec:attack:chain"},
            ],
        },
        {
            "key": "sec-report",
            "label": "认证报告",
            "permission": "sec:report:view",
            "feature_flag": "sec_report",
            "children": [
                {"key": "sec-report-list", "label": "报告列表", "permission": "sec:report:view"},
                {"key": "sec-report-export", "label": "导出报告", "permission": "sec:report:export"},
                {"key": "sec-report-evidence", "label": "证据下钻", "permission": "sec:report:evidence:view"},
            ],
        },
        {
            "key": "sec-certificate",
            "label": "认证证书",
            "permission": "sec:cert:verify",
            "feature_flag": "sec_certificate",
            "children": [
                {"key": "sec-certificate-list", "label": "证书列表", "permission": "sec:cert:verify"},
                {"key": "sec-certificate-issue", "label": "颁发证书", "permission": "sec:cert:issue"},
                {"key": "sec-certificate-revoke", "label": "撤销证书", "permission": "sec:cert:revoke"},
            ],
        },
        {
            "key": "sec-config",
            "label": "认证配置",
            "permission": "sec:config:manage",
            "feature_flag": "sec_config",
        },
        {
            "key": "sec-audit",
            "label": "认证审计",
            "permission": "sec:audit:view",
            "feature_flag": "sec_audit",
        },
        {
            "key": "sec-platform-access",
            "label": "平台访问申请",
            "permission": "sec:platform:access:request",
            "feature_flag": "sec_platform_access",
        },
        {
            "key": "sec-redis-scan",
            "label": "Redis Key 扫描",
            "permission": "sec:redis:scan",
            "feature_flag": "sec_redis_scan",
        },
        {
            "key": "sec-join-test",
            "label": "JOIN 泄露测试",
            "permission": "sec:join:test",
            "feature_flag": "sec_join_test",
        },
    ],
}